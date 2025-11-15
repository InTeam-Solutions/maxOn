"""
Simple HTTP health check server for Railway deployment
Runs alongside the Telegram bot to provide a health endpoint
"""
import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def health_handler(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "service": "api-gateway"})

async def start_health_server(port=8080):
    """Start health check HTTP server"""
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', health_handler)  # Railway might check root as well

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Health check server started on port {port}")

    return runner
