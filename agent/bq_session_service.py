"""Odin v2 - BigQuery-backed Session Service for ADK.
Persists chat history to BigQuery so session memory is preserved across Cloud Run container recycles.
"""
import json
import logging
from typing import Any, Optional
from google.adk.sessions.base_session_service import BaseSessionService, GetSessionConfig, ListSessionsResponse
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.cloud import bigquery
from agent.bq_client import client, PROJECT, DATASET

logger = logging.getLogger("bq_session_service")

class BigQuerySessionService(BaseSessionService):
    def __init__(self):
        self.project = PROJECT
        self.dataset = DATASET
        self.table_ref = f"{self.project}.{self.dataset}.chat_sessions"
        self._ensure_table()

    def _ensure_table(self):
        try:
            sql = f"""
            CREATE TABLE IF NOT EXISTS `{self.table_ref}` (
                session_key STRING,
                session_json STRING,
                update_time TIMESTAMP
            )
            """
            client.query(sql).result()
            logger.info(f"BigQuery session table verified: {self.table_ref}")
        except Exception as e:
            logger.error(f"Failed to create/verify session table in BigQuery: {e}")

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        sid = session_id or f"sess_{user_id}"
        session = Session(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=0.0
        )
        await self._save_session(session)
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        key = f"{app_name}:{user_id}:{session_id}"
        sql = f"SELECT session_json FROM `{self.table_ref}` WHERE session_key = @key LIMIT 1"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("key", "STRING", key)
            ]
        )
        try:
            rows = list(client.query(sql, job_config=job_config).result())
            if not rows:
                return None
            session_json = rows[0]["session_json"]
            session = Session.model_validate_json(session_json)
            
            # Apply filtering config if present
            if config:
                if config.num_recent_events is not None:
                    if config.num_recent_events == 0:
                        session.events = []
                    else:
                        session.events = session.events[-config.num_recent_events:]
                if config.after_timestamp is not None:
                    session.events = [e for e in session.events if e.timestamp >= config.after_timestamp]
            return session
        except Exception as e:
            logger.error(f"Error loading session {key} from BigQuery: {e}")
            return None

    async def append_event(self, session: Session, event: Event) -> Event:
        # First append in memory using base class logic
        ret_event = await super().append_event(session, event)
        # Then save updated session back to BigQuery
        await self._save_session(session)
        return ret_event

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        key = f"{app_name}:{user_id}:{session_id}"
        sql = f"DELETE FROM `{self.table_ref}` WHERE session_key = @key"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("key", "STRING", key)
            ]
        )
        try:
            client.query(sql, job_config=job_config).result()
            logger.info(f"Deleted session key {key} from BigQuery")
        except Exception as e:
            logger.error(f"Error deleting session {key} from BigQuery: {e}")

    async def list_sessions(self, *, app_name: str, user_id: Optional[str] = None) -> ListSessionsResponse:
        sql = f"SELECT session_json FROM `{self.table_ref}`"
        params = []
        if user_id:
            sql += " WHERE session_key LIKE @pattern"
            params.append(bigquery.ScalarQueryParameter("pattern", "STRING", f"{app_name}:{user_id}:%"))
        else:
            sql += " WHERE session_key LIKE @pattern"
            params.append(bigquery.ScalarQueryParameter("pattern", "STRING", f"{app_name}:%"))
            
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        try:
            rows = list(client.query(sql, job_config=job_config).result())
            sessions = []
            for r in rows:
                sessions.append(Session.model_validate_json(r["session_json"]))
            return ListSessionsResponse(sessions=sessions)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return ListSessionsResponse()

    async def _save_session(self, session: Session):
        key = f"{session.app_name}:{session.user_id}:{session.id}"
        # Serialize to JSON string
        session_json = session.model_dump_json()
        
        # Use MERGE statement to perform upsert in BigQuery
        sql = f"""
        MERGE `{self.table_ref}` T
        USING (SELECT @key AS session_key, @json AS session_json) S
        ON T.session_key = S.session_key
        WHEN MATCHED THEN
          UPDATE SET session_json = S.session_json, update_time = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
          INSERT (session_key, session_json, update_time) VALUES (S.session_key, S.session_json, CURRENT_TIMESTAMP())
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("key", "STRING", key),
                bigquery.ScalarQueryParameter("json", "STRING", session_json)
            ]
        )
        try:
            client.query(sql, job_config=job_config).result()
        except Exception as e:
            logger.error(f"Error saving session {key} to BigQuery: {e}")
