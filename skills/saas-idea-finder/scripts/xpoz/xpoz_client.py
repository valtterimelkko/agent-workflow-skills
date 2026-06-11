#!/usr/bin/env python3
"""
HTTP-based MCP client for Xpoz social media API.

Xpoz uses HTTP transport (not stdio) with Bearer token authentication.
API endpoint: https://mcp.xpoz.ai/mcp
Uses SSE (Server-Sent Events) for responses.

Important: Xpoz operations are async - they return operationIds that must be polled
via checkOperationStatus until completion.
"""
import aiohttp
import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

try:
    from .xpoz_credentials import XpozCredentialLoader, CredentialNotFoundError
except ImportError:
    from xpoz_credentials import XpozCredentialLoader, CredentialNotFoundError


class XpozMCPClient:
    """HTTP MCP client for Xpoz social media API."""

    MCP_URL = "https://mcp.xpoz.ai/mcp"
    TIMEOUT = aiohttp.ClientTimeout(total=180)  # 3 minutes total timeout
    POLL_INTERVAL = 3  # Seconds between polls (check more frequently)
    MAX_POLL_TIME = 600  # Maximum 10 minutes to wait for operation

    def __init__(self):
        self.credential_loader = XpozCredentialLoader()
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
        self._tools: List[Dict] = []

    async def connect(self, verify: bool = False) -> List[Dict]:
        """
        Initialize HTTP session with Bearer auth.

        Args:
            verify: Whether to verify by listing tools (may trigger rate limits)

        Returns:
            List of available tools (empty if verify=False)

        Raises:
            CredentialNotFoundError: If token not found
            XpozAPIError: If connection fails
        """
        self._token = self.credential_loader.load()

        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=self.TIMEOUT
        )

        if verify:
            # Verify connection by listing tools
            self._tools = await self.list_tools()
            tool_names = [t.get('name', 'unknown') for t in self._tools]
            print(f"Connected to Xpoz MCP. Available tools: {tool_names}")
        else:
            print("Connected to Xpoz MCP (verification skipped)")

        return self._tools

    def _parse_sse_response(self, text: str) -> Dict:
        """
        Parse Server-Sent Events response.
        SSE format: data: {...}\n\n
        """
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('data: '):
                json_str = line[6:]  # Remove 'data: ' prefix
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        # If no data lines found, try parsing entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise XpozAPIError(f"Failed to parse response: {e}")

    async def list_tools(self) -> List[Dict]:
        """
        List available MCP tools.

        Returns:
            List of tool definitions
        """
        if not self._session:
            raise XpozAPIError("Not connected. Call connect() first.")

        try:
            async with self._session.post(
                self.MCP_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
            ) as resp:
                if resp.status == 401:
                    raise XpozAPIError("Token expired or invalid. Re-authenticate at xpoz.ai")
                if resp.status == 429:
                    raise XpozAPIError("Rate limited. Wait before retrying.")
                if resp.status != 200:
                    text = await resp.text()
                    raise XpozAPIError(f"HTTP {resp.status}: {text}")

                text = await resp.text()
                data = self._parse_sse_response(text)
                
                if "error" in data:
                    raise XpozAPIError(f"MCP Error: {data['error']}")

                return data.get("result", {}).get("tools", [])
        except aiohttp.ClientError as e:
            raise XpozAPIError(f"Connection error: {e}")

    def _extract_operation_id(self, content: List[Dict]) -> Optional[str]:
        """Extract operationId from async response content."""
        if not content or len(content) == 0:
            return None
        
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text = item.get('text', '')
                # Look for operationId in the text
                match = re.search(r'operationId:\s*(\S+)', text)
                if match:
                    return match.group(1)
        return None

    async def _poll_operation(self, operation_id: str) -> Dict[str, Any]:
        """
        Poll checkOperationStatus until operation completes.
        
        Args:
            operation_id: The operation ID to poll
            
        Returns:
            Final operation result
            
        Raises:
            XpozAPIError: If operation fails or times out
        """
        start_time = asyncio.get_event_loop().time()
        poll_count = 0
        
        while True:
            # Check if we've exceeded max poll time
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.MAX_POLL_TIME:
                raise XpozAPIError(f"Operation {operation_id} timed out after {self.MAX_POLL_TIME}s")
            
            try:
                result = await self._call_check_operation(operation_id)
            except XpozAPIError as e:
                # Check if rate limited during polling
                if "rate limit" in str(e).lower():
                    raise XpozAPIError(f"Rate limited while polling operation {operation_id}")
                raise
            
            # Parse the result to check status
            content = result.get("content", [])
            status = self._extract_status(content)
            
            if status == "completed":
                return result
            elif status in ("failed", "cancelled", "error"):
                raise XpozAPIError(f"Operation {operation_id} {status}")
            elif status == "rate_limited":
                raise XpozAPIError(f"Rate limited during operation {operation_id}")
            
            # Still running, wait and poll again
            poll_count += 1
            await asyncio.sleep(self.POLL_INTERVAL)

    def _extract_status(self, content: List[Dict]) -> str:
        """Extract status from operation response content."""
        if not content:
            return "unknown"
        
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text = item.get('text', '')
                # Look for status field
                match = re.search(r'status:\s*(\w+)', text)
                if match:
                    return match.group(1).lower()
        return "running"  # Default to running if can't determine

    async def _call_check_operation(self, operation_id: str) -> Dict[str, Any]:
        """Call checkOperationStatus tool."""
        async with self._session.post(
            self.MCP_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "checkOperationStatus",
                    "arguments": {"operationId": operation_id}
                }
            }
        ) as resp:
            text = await resp.text()
            return self._parse_sse_response(text)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        skip_polling: bool = False
    ) -> Dict[str, Any]:
        """
        Call an MCP tool with automatic polling for async operations.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            skip_polling: If True, return immediately with operationId (don't poll)

        Returns:
            Tool result (after polling if async, or immediately if skip_polling)

        Raises:
            XpozAPIError: If call fails
        """
        if not self._session:
            raise XpozAPIError("Not connected. Call connect() first.")

        try:
            async with self._session.post(
                self.MCP_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
            ) as resp:
                if resp.status == 401:
                    raise XpozAPIError("Token expired or invalid. Re-authenticate at xpoz.ai")
                if resp.status == 429:
                    raise XpozAPIError("Rate limited. Wait before retrying.")
                if resp.status != 200:
                    text = await resp.text()
                    raise XpozAPIError(f"HTTP {resp.status}: {text}")

                text = await resp.text()
                data = self._parse_sse_response(text)
                
                if "error" in data:
                    raise XpozAPIError(f"Tool error: {data['error']}")

                result = data.get("result", {})
                
                # Check if this is an async operation that needs polling
                content = result.get("content", [])
                operation_id = self._extract_operation_id(content)
                
                if operation_id and not skip_polling:
                    # This is an async operation, poll for results
                    print(f"  Waiting for operation {operation_id[:30]}...")
                    result = await self._poll_operation(operation_id)
                
                return result
        except aiohttp.ClientError as e:
            raise XpozAPIError(f"Connection error: {e}")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class XpozAPIError(Exception):
    """Raised when Xpoz API call fails."""
    pass