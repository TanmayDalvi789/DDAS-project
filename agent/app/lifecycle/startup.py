"""Agent lifecycle management - startup sequence."""

import logging
import sys
import uuid

from app.permissions.checker import PermissionValidator
from app.permissions.errors import PermissionError
from app.proxy_events.event_listener import ProxyEventListener
from app.proxy_events.adapters import HTTPEventAdapter
from app.proxy_events.handler import EventHandler
from app.cache.database import CacheDatabase
from app.cache.repository import CacheRepository

logger = logging.getLogger(__name__)


def validate_permissions(config) -> bool:
    """
    Validate system permissions (FAIL-CLOSED).
    
    This runs FIRST before any other initialization.
    If validation fails, agent startup is aborted cleanly.
    
    Args:
        config: Agent configuration object
    
    Returns:
        True if validation passes
        
    Raises:
        PermissionError: If validation fails (will be caught by caller)
    """
    logger.info("=" * 50)
    logger.info("STEP 1: Permission Validation")
    logger.info("=" * 50)
    
    validator = PermissionValidator(
        backend_host=config.backend_url.split("://")[-1].split(":")[0] or "localhost",
        backend_port=int(config.backend_url.split(":")[-1]) if ":" in config.backend_url else 8001
    )
    
    try:
        validator.validate_all()
        logger.info("✓ All permissions granted - proceeding with startup")
        return True
    except PermissionError as e:
        logger.critical(f"✗ Permission validation failed")
        logger.critical(f"Error: {e}")
        logger.critical("-" * 50)
        raise


def register_agent(config) -> tuple:
    """
    Register agent with backend or load existing ID.
    
    Returns:
        tuple: (agent_id, config_dict)
    """
    logger.info("=" * 50)
    logger.info("STEP 2: Agent Registration")
    logger.info("=" * 50)
    
    # Initialize metadata store for agent_id persistence
    metadata_store = AgentMetadataStore(config.cache_path)
    
    # Try to load existing agent_id
    agent_id = metadata_store.get_agent_id()
    
    if agent_id:
        logger.info(f"✓ Reusing existing agent_id: {agent_id}")
    else:
        # Generate new agent_id
        agent_id = str(uuid.uuid4())
        logger.info(f"✓ Generated new agent_id: {agent_id}")
    
    # Setup backend client
    auth = BackendAuth(config.backend_api_key)
    reg_client = RegistrationClient(config.backend_url, auth.get_headers())
    config_client = ConfigClient(config.backend_url, auth.get_headers())
    
    # Register with backend (or confirm existing registration)
    reg_result = reg_client.register_agent(agent_id, config.agent_name)
    
    if reg_result:
        # Store agent_id as registered
        metadata_store.store_agent_id(agent_id, registered=True)
        
        # Fetch and cache initial config
        initial_config = config_client.fetch_config(agent_id)
        logger.info(f"✓ Agent registered with backend")
        
        return agent_id, initial_config or {}, metadata_store, config_client, auth
    else:
        # Registration failed, but store agent_id anyway
        # Agent will retry on next heartbeat
        metadata_store.store_agent_id(agent_id, registered=False)
        logger.warning("Agent registration with backend failed - will retry on heartbeat")
        
        return agent_id, {}, metadata_store, config_client, auth


def start_heartbeat(agent_id: str, config, auth_headers: dict) -> HeartbeatLoop:
    """
    Start background heartbeat loop.
    
    Args:
        agent_id: Agent identifier
        config: Agent configuration
        auth_headers: Authentication headers
    
    Returns:
        HeartbeatLoop instance
    """
    logger.info("=" * 50)
    logger.info("STEP 3: Start Heartbeat")
    logger.info("=" * 50)
    
    heartbeat = HeartbeatLoop(
        agent_id=agent_id,
        backend_url=config.backend_url,
        auth_headers=auth_headers,
        interval_seconds=60,  # Default 60s interval
    )
    
    heartbeat.start()
    logger.info("✓ Heartbeat loop started")
    
    return heartbeat


def start_proxy_event_listener(config) -> tuple:
    """
    Start proxy event listener and initialize cache (STEP-3 + STEP-4).
    
    Initializes:
    - Cache database for storing features
    - Event handler for processing + feature extraction
    - HTTP listener for receiving proxy events
    
    Args:
        config: Agent configuration
    
    Returns:
        tuple: (listener, cache_db) instances
    """
    logger.info("=" * 50)
    logger.info("STEP 4: Event Listener + Feature Extraction")
    logger.info("=" * 50)
    
    # Initialize cache database (STEP-4)
    logger.debug(f"Initializing cache: {config.cache_path}")
    cache_db = CacheDatabase(config.cache_path)
    cache_repo = CacheRepository(cache_db)
    
    # Create event handler with feature extraction (STEP-3 + STEP-4)
    adapter = HTTPEventAdapter()
    
    def on_valid_event(event, features=None):
        """Process valid normalized event with extracted features."""
        logger.debug(
            f"Event processed: type={event.get('event_type')}, "
            f"ts={event.get('timestamp')}"
        )
        if features:
            logger.debug(
                f"Features extracted: "
                f"exact={bool(features.get('exact'))}, "
                f"fuzzy={bool(features.get('fuzzy'))}, "
                f"semantic={bool(features.get('semantic'))}"
            )
        # TODO Phase-5: Forward to decision engine
    
    handler = EventHandler(
        adapter,
        on_valid_event=on_valid_event,
        cache_repo=cache_repo,
        config=config
    )
    
    # Create and start listener
    listener = ProxyEventListener(
        port=config.proxy_event_port,
        event_handler_callback=handler.handle,
    )
    
    listener.start()
    logger.info(f"✓ Event listener started (port={config.proxy_event_port})")
    logger.info(f"✓ Feature extraction enabled")
    logger.info(f"✓ Cache database initialized")
    
    return listener, cache_db


def bootstrap_agent(config):
    """
    Bootstrap the agent after permission validation.
    
    Startup sequence:
    1. Validate permissions (FAIL-CLOSED)
    2. Register agent with backend
    3. Start heartbeat loop
    4. Start proxy event listener + feature extraction
    5. TODO Phase-5: Start decision engine
    6. TODO Phase-6: Start response handler
    
    Args:
        config: Agent configuration
    
    Raises:
        PermissionError: If permission validation fails
        Exception: If bootstrap fails
    """
    heartbeat_loop = None
    event_listener = None
    cache_db = None
    
    try:
        # STEP 1: PERMISSION VALIDATION (FAIL-CLOSED)
        validate_permissions(config)
        
        # STEP 2: AGENT REGISTRATION
        agent_id, agent_config, metadata_store, config_client, auth = register_agent(config)
        
        # STEP 3: START HEARTBEAT
        heartbeat_loop = start_heartbeat(agent_id, config, auth.get_headers())
        
        # STEP 4: START PROXY EVENT LISTENER + FEATURE EXTRACTION
        event_listener, cache_db = start_proxy_event_listener(config)
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("STEP 5: Decision Engine")
        logger.info("=" * 50)
        # TODO Phase-5: Start decision engine
        logger.info("Decision engine: TODO")
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("STEP 6: Response Handler")
        logger.info("=" * 50)
        # TODO Phase-6: Start response handler
        logger.info("Response handler: TODO")
        
        logger.info("")
        logger.info("✓ Agent bootstrap complete")
        logger.info(f"Agent: {config.agent_id} ({config.agent_name})")
        logger.info(f"Agent ID: {agent_id}")
        logger.info(f"Heartbeat: Running")
        logger.info(f"Event Listener: Running (port={config.proxy_event_port})")
        logger.info(f"Feature Extraction: Enabled")
        logger.info(f"Cache Database: Active")
        
        # Keep the application running
        # (In production, this would be a long-running service loop)
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            if heartbeat_loop:
                heartbeat_loop.stop()
            if event_listener:
                event_listener.stop()
            if cache_db:
                cache_db.close()
        
    except PermissionError as e:
        logger.critical(f"Startup aborted: {e}")
        raise
    except Exception as e:
        logger.critical(f"Bootstrap failed: {e}", exc_info=True)
        if heartbeat_loop:
            heartbeat_loop.stop()
        if event_listener:
            event_listener.stop()
        if cache_db:
            cache_db.close()
        raise

