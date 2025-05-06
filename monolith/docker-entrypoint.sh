#!/bin/bash
set -e

# Apply database migrations
if [ "$APPLY_MIGRATIONS" = "true" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
    echo "Migrations applied successfully"
fi

# Wait for other services if needed
if [ "$WAIT_FOR_DEPENDENCIES" = "true" ]; then
    echo "Waiting for dependencies to be ready..."
    
    # Wait for PostgreSQL
    if [ ! -z "$DATABASE_URL" ]; then
        echo "Waiting for PostgreSQL..."
        
        # Extract host and port from DATABASE_URL
        if [[ $DATABASE_URL == postgresql* ]]; then
            # Extract host:port part
            HOST_PORT=$(echo $DATABASE_URL | sed -E 's/.*@([^/]+)\/.*/\1/')
            HOST=$(echo $HOST_PORT | cut -d':' -f1)
            PORT=$(echo $HOST_PORT | cut -d':' -f2)
            
            # Default to standard PostgreSQL port if not specified
            if [ -z "$PORT" ]; then
                PORT=5432
            fi
            
            echo "Waiting for PostgreSQL at $HOST:$PORT..."
            
            # Wait for PostgreSQL to be ready
            until nc -z -v -w30 $HOST $PORT; do
                echo "PostgreSQL at $HOST:$PORT is not reachable yet. Waiting..."
                sleep 2
            done
            
            echo "PostgreSQL is ready!"
        fi
    fi
    
    # Wait for Redis
    if [ ! -z "$REDIS_URL" ]; then
        echo "Waiting for Redis..."
        
        # Extract host and port from REDIS_URL
        if [[ $REDIS_URL == redis* ]]; then
            # Extract host:port part
            HOST_PORT=$(echo $REDIS_URL | sed -E 's/.*redis:\/\/([^/]+).*/\1/')
            HOST=$(echo $HOST_PORT | cut -d':' -f1)
            PORT=$(echo $HOST_PORT | cut -d':' -f2)
            
            # Default to standard Redis port if not specified
            if [ -z "$PORT" ]; then
                PORT=6379
            fi
            
            echo "Waiting for Redis at $HOST:$PORT..."
            
            # Wait for Redis to be ready
            until nc -z -v -w30 $HOST $PORT; do
                echo "Redis at $HOST:$PORT is not reachable yet. Waiting..."
                sleep 2
            done
            
            echo "Redis is ready!"
        fi
    fi
    
    # Wait for Kafka
    if [ ! -z "$KAFKA_BOOTSTRAP_SERVERS" ]; then
        echo "Waiting for Kafka..."
        
        # Loop through Kafka bootstrap servers
        IFS=',' read -ra SERVERS <<< "$KAFKA_BOOTSTRAP_SERVERS"
        for SERVER in "${SERVERS[@]}"; do
            HOST=$(echo $SERVER | cut -d':' -f1)
            PORT=$(echo $SERVER | cut -d':' -f2)
            
            echo "Waiting for Kafka at $HOST:$PORT..."
            
            # Wait for Kafka to be ready
            until nc -z -v -w30 $HOST $PORT; do
                echo "Kafka at $HOST:$PORT is not reachable yet. Waiting..."
                sleep 2
            done
            
            echo "Kafka is ready!"
            break  # Once one Kafka broker is reachable, we can proceed
        done
    fi
    
    echo "All dependencies are ready!"
fi

# Run any additional initialization
if [ "$RUN_INIT_SCRIPT" = "true" ] && [ -f "/app/scripts/init.py" ]; then
    echo "Running initialization script..."
    python /app/scripts/init.py
    echo "Initialization script completed"
fi

# Execute the CMD
echo "Starting the application..."
exec "$@" 