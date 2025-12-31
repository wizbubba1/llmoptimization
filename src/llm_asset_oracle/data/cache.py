"""Caching layer for LLM responses and market data."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite

from llm_asset_oracle.core.models import Asset, ConsensusScore, LLMResponse

logger = logging.getLogger(__name__)


class DataCache:
    """
    SQLite-based cache for LLM responses and analysis results.

    Provides:
    - Persistent caching of LLM responses
    - TTL-based expiration
    - Historical score tracking
    """

    def __init__(self, db_path: str = "./data/llm_oracle.db"):
        """Initialize cache with database path."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self):
        """Initialize database tables."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # LLM Responses cache
            await db.execute("""
                CREATE TABLE IF NOT EXISTS llm_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_symbol TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # Consensus scores history
            await db.execute("""
                CREATE TABLE IF NOT EXISTS consensus_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_symbol TEXT NOT NULL,
                    los_score REAL NOT NULL,
                    consensus_strength REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    models_queried INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_responses_symbol_expires
                ON llm_responses(asset_symbol, expires_at)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_symbol
                ON consensus_history(asset_symbol, created_at)
            """)

            await db.commit()
            self._initialized = True

    async def get_cached_responses(
        self, asset_symbol: str, max_age_seconds: int = 3600
    ) -> list[LLMResponse]:
        """
        Get cached LLM responses for an asset.

        Args:
            asset_symbol: The asset symbol
            max_age_seconds: Maximum age of cached responses

        Returns:
            List of cached LLMResponse objects
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT response_json FROM llm_responses
                WHERE asset_symbol = ?
                AND expires_at > datetime('now')
                ORDER BY created_at DESC
                """,
                (asset_symbol.upper(),),
            )

            rows = await cursor.fetchall()
            responses = []

            for row in rows:
                try:
                    data = json.loads(row["response_json"])
                    responses.append(LLMResponse.model_validate(data))
                except Exception as e:
                    logger.warning(f"Failed to parse cached response: {e}")

            return responses

    async def cache_response(
        self, response: LLMResponse, ttl_seconds: int = 3600
    ):
        """
        Cache an LLM response.

        Args:
            response: The LLM response to cache
            ttl_seconds: Time-to-live in seconds
        """
        await self.initialize()

        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO llm_responses
                (asset_symbol, provider, model, response_json, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    response.asset_symbol.upper(),
                    response.provider,
                    response.model,
                    response.model_dump_json(),
                    expires_at.isoformat(),
                ),
            )
            await db.commit()

    async def cache_responses(
        self, responses: list[LLMResponse], ttl_seconds: int = 3600
    ):
        """Cache multiple LLM responses."""
        for response in responses:
            await self.cache_response(response, ttl_seconds)

    async def save_consensus(self, consensus: ConsensusScore):
        """
        Save consensus score to history.

        Args:
            consensus: The consensus score to save
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO consensus_history
                (asset_symbol, los_score, consensus_strength, recommendation, models_queried)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    consensus.asset.symbol.upper(),
                    consensus.los_score,
                    consensus.consensus_strength,
                    consensus.recommendation,
                    consensus.total_models_queried,
                ),
            )
            await db.commit()

    async def get_historical_scores(
        self, asset_symbol: str, days: int = 30
    ) -> list[dict]:
        """
        Get historical LOS scores for an asset.

        Args:
            asset_symbol: The asset symbol
            days: Number of days of history

        Returns:
            List of historical score records
        """
        await self.initialize()

        cutoff = datetime.utcnow() - timedelta(days=days)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT los_score, consensus_strength, recommendation, created_at
                FROM consensus_history
                WHERE asset_symbol = ?
                AND created_at > ?
                ORDER BY created_at DESC
                """,
                (asset_symbol.upper(), cutoff.isoformat()),
            )

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_score_trend(self, asset_symbol: str) -> Optional[str]:
        """
        Determine the score trend for an asset.

        Returns:
            "up", "down", "stable", or None if insufficient data
        """
        history = await self.get_historical_scores(asset_symbol, days=7)

        if len(history) < 2:
            return None

        recent_scores = [h["los_score"] for h in history[:5]]
        older_scores = [h["los_score"] for h in history[5:10]] if len(history) > 5 else None

        if not older_scores:
            return None

        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)

        diff = recent_avg - older_avg

        if diff > 5:
            return "up"
        elif diff < -5:
            return "down"
        else:
            return "stable"

    async def cleanup_expired(self):
        """Remove expired cache entries."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM llm_responses
                WHERE expires_at < datetime('now')
            """)
            await db.commit()

    async def get_top_assets_by_history(self, limit: int = 10) -> list[dict]:
        """
        Get top assets by their most recent LOS scores.

        Args:
            limit: Maximum number of assets to return

        Returns:
            List of assets with their latest scores
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get the latest score for each asset
            cursor = await db.execute(
                """
                SELECT asset_symbol, los_score, consensus_strength, recommendation, created_at
                FROM consensus_history ch1
                WHERE created_at = (
                    SELECT MAX(created_at)
                    FROM consensus_history ch2
                    WHERE ch2.asset_symbol = ch1.asset_symbol
                )
                ORDER BY los_score DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
