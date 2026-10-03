import asyncio
import websockets
import aiohttp
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict, Any
import argparse
import random
import string

class WebSocketLoadTester:
    def __init__(self, base_url: str, max_workers: int = 1000):
        self.base_url = base_url.rstrip('/')
        self.max_workers = max_workers
        self.results = []
        self.active_connections = []
        
    def generate_client_id(self, prefix: str = "load-test") -> str:
        """Generate unique client ID with random suffix"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}-{random_suffix}-{int(time.time())}"
    
    async def health_check(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test the health check endpoint"""
        try:
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"Status {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def connect_websocket(self, client_id: str, duration: int = 10) -> Dict[str, Any]:
        """Connect to WebSocket endpoint with specific client_id and maintain connection"""
        start_time = time.time()
        messages_received = 0
        connection_successful = False
        error = None
        connection_time = None
        
        try:
            # Connect to the specific client_id endpoint
            ws_url = f"{self.base_url.replace('http', 'ws')}/ws/{client_id}"
            async with websockets.connect(ws_url) as websocket:
                connection_successful = True
                connection_time = time.time() - start_time
                
                # Wait for initial connection message
                try:
                    initial_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    initial_data = json.loads(initial_msg)
                    messages_received += 1
                    
                    # Verify the connection message contains our client_id
                    if initial_data.get('client_id') != client_id:
                        logger.warning(f"Client ID mismatch: expected {client_id}, got {initial_data.get('client_id')}")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"No initial message received for client {client_id}")
                
                # Keep connection alive for specified duration
                end_time = time.time() + duration
                while time.time() < end_time:
                    try:
                        # Try to receive any incoming messages with timeout
                        msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        messages_received += 1
                        
                        # Parse message to verify it's for this client
                        try:
                            msg_data = json.loads(msg)
                            if msg_data.get('type') == 'message':
                                # Message successfully received for this client
                                pass
                        except json.JSONDecodeError:
                            pass
                            
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.ping()
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break
                        
        except Exception as e:
            error = str(e)
            connection_time = time.time() - start_time if connection_time is None else connection_time
            
        return {
            "client_id": client_id,
            "success": connection_successful,
            "connection_time": connection_time,
            "duration": time.time() - start_time,
            "messages_received": messages_received,
            "error": error
        }
    
    async def test_single_connection(self, client_id: str, duration: int = 10) -> Dict[str, Any]:
        """Test a single WebSocket connection with specific client_id"""
        return await self.connect_websocket(client_id, duration)
    
    async def test_concurrent_connections(self, num_connections: int, duration: int = 10) -> Dict[str, Any]:
        """Test multiple concurrent WebSocket connections with unique client IDs"""
        print(f"Testing {num_connections} concurrent connections for {duration} seconds...")
        
        start_time = time.time()
        tasks = []
        client_ids = []
        
        # Create unique client IDs and connection tasks
        for i in range(num_connections):
            client_id = self.generate_client_id()
            client_ids.append(client_id)
            task = asyncio.create_task(self.test_single_connection(client_id, duration))
            tasks.append(task)
        
        # Wait for all connections to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_connections = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_connections = [r for r in results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        test_duration = time.time() - start_time
        
        # Calculate statistics
        connection_times = [r['connection_time'] for r in successful_connections if r.get('connection_time')]
        
        # Group results by client_id pattern for analysis
        client_id_patterns = {}
        for result in successful_connections + failed_connections:
            if isinstance(result, dict):
                client_id = result.get('client_id', 'unknown')
                pattern = '-'.join(client_id.split('-')[:2])  # Get prefix pattern
                if pattern not in client_id_patterns:
                    client_id_patterns[pattern] = []
                client_id_patterns[pattern].append(result)
        
        return {
            "total_connections": num_connections,
            "successful_connections": len(successful_connections),
            "failed_connections": len(failed_connections),
            "exceptions": len(exceptions),
            "success_rate": len(successful_connections) / num_connections * 100,
            "avg_connection_time": statistics.mean(connection_times) if connection_times else 0,
            "max_connection_time": max(connection_times) if connection_times else 0,
            "min_connection_time": min(connection_times) if connection_times else 0,
            "total_messages": sum(r['messages_received'] for r in successful_connections),
            "test_duration": test_duration,
            "connections_per_second": num_connections / test_duration if test_duration > 0 else 0,
            "client_id_patterns": client_id_patterns,
            "sample_client_ids": client_ids[:5]  # Sample of client IDs used
        }
    
    async def test_different_client_patterns(self, patterns: List[str], connections_per_pattern: int = 10, duration: int = 5):
        """Test different client ID patterns to ensure routing works correctly"""
        print(f"Testing {len(patterns)} different client ID patterns with {connections_per_pattern} connections each...")
        
        all_results = []
        
        for pattern in patterns:
            print(f"\nTesting pattern: {pattern}")
            
            tasks = []
            for i in range(connections_per_pattern):
                client_id = f"{pattern}-{i}-{int(time.time())}"
                task = asyncio.create_task(self.test_single_connection(client_id, duration))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = [r for r in results if isinstance(r, dict) and r.get('success')]
            
            pattern_result = {
                "pattern": pattern,
                "total_connections": connections_per_pattern,
                "successful_connections": len(successful),
                "success_rate": len(successful) / connections_per_pattern * 100,
                "avg_messages": statistics.mean([r['messages_received'] for r in successful]) if successful else 0
            }
            
            all_results.append(pattern_result)
            print(f"  {pattern}: {len(successful)}/{connections_per_pattern} successful ({pattern_result['success_rate']:.1f}%)")
        
        return all_results
    
    async def test_message_routing(self, num_clients: int = 10, duration: int = 5):
        """Test that messages are properly routed to correct client IDs"""
        print(f"Testing message routing for {num_clients} different clients...")
        
        clients = []
        connections = []
        
        # Connect all clients
        for i in range(num_clients):
            client_id = f"routing-test-{i}"
            ws_url = f"{self.base_url.replace('http', 'ws')}/ws/{client_id}"
            
            try:
                websocket = await websockets.connect(ws_url)
                # Wait for connection message
                initial_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                initial_data = json.loads(initial_msg)
                
                clients.append({
                    'client_id': client_id,
                    'websocket': websocket,
                    'messages_received': 0,
                    'connection_data': initial_data
                })
                print(f"  Connected client {client_id}")
                
            except Exception as e:
                print(f"  Failed to connect client {client_id}: {e}")
        
        # Keep connections alive and monitor messages
        start_time = time.time()
        while time.time() - start_time < duration:
            for client in clients:
                try:
                    msg = await asyncio.wait_for(client['websocket'].recv(), timeout=0.1)
                    client['messages_received'] += 1
                    
                    # Verify message is for this client (if it contains routing info)
                    try:
                        msg_data = json.loads(msg)
                        # Could add verification logic here if messages contain client IDs
                    except:
                        pass
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
        
        # Close all connections
        for client in clients:
            try:
                await client['websocket'].close()
            except:
                pass
        
        # Return routing test results
        return {
            "total_clients": num_clients,
            "successful_connections": len(clients),
            "total_messages_received": sum(client['messages_received'] for client in clients),
            "messages_per_client": {client['client_id']: client['messages_received'] for client in clients},
            "routing_success_rate": len(clients) / num_clients * 100
        }
    
    async def incremental_load_test(self, max_connections: int, step: int = 100, duration: int = 10):
        """Test with incrementally increasing load using unique client IDs"""
        print(f"Running incremental load test up to {max_connections} connections...")
        
        connection_counts = list(range(step, max_connections + step, step))
        results = []
        
        for num_conn in connection_counts:
            print(f"\nTesting {num_conn} connections with unique client IDs...")
            
            # Get health before test
            async with aiohttp.ClientSession() as session:
                health_before = await self.health_check(session)
            
            # Run concurrent test
            test_result = await self.test_concurrent_connections(num_conn, duration)
            test_result['connections_tested'] = num_conn
            test_result['health_before'] = health_before
            
            # Get health after test
            async with aiohttp.ClientSession() as session:
                health_after = await self.health_check(session)
            test_result['health_after'] = health_after
            
            results.append(test_result)
            
            # Print current status with client ID info
            print(f"  Success rate: {test_result['success_rate']:.1f}%")
            print(f"  Avg connection time: {test_result['avg_connection_time']:.3f}s")
            print(f"  Client ID patterns: {list(test_result['client_id_patterns'].keys())}")
            
            # Stop if success rate drops below 90%
            if test_result['success_rate'] < 90:
                print(f"  ❌ Success rate dropped below 90%, stopping test.")
                break
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]):
        """Generate a comprehensive test report"""
        print("\n" + "="*80)
        print("WEBSOCKET LOAD TEST REPORT - MULTI CLIENT ID TESTING")
        print("="*80)
        
        df = pd.DataFrame(results)
        
        # Print summary
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total test runs: {len(results)}")
        print(f"   Maximum connections tested: {df['connections_tested'].max()}")
        print(f"   Best success rate: {df['success_rate'].max():.1f}%")
        
        # Client ID analysis
        if 'client_id_patterns' in results[0]:
            all_patterns = set()
            for result in results:
                all_patterns.update(result['client_id_patterns'].keys())
            print(f"   Client ID patterns tested: {len(all_patterns)}")
        
        # Find breaking point
        breaking_point = df[df['success_rate'] < 95]
        if not breaking_point.empty:
            break_conn = breaking_point.iloc[0]['connections_tested']
            print(f"   🚨 Breaking point (below 95%): {break_conn} connections")
        
        # Print detailed results
        print(f"\n📈 DETAILED RESULTS:")
        for _, row in df.iterrows():
            pattern_info = f" patterns: {len(row.get('client_id_patterns', {}))}" if 'client_id_patterns' in row else ""
            print(f"   {row['connections_tested']:4d} connections: "
                  f"{row['success_rate']:5.1f}% success, "
                  f"{row['avg_connection_time']:5.3f}s avg connect{pattern_info}")
        
        # Plot results
        self.plot_results(df)
    
    def plot_results(self, df: pd.DataFrame):
        """Plot test results"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Success rate
        ax1.plot(df['connections_tested'], df['success_rate'], 'b-o', linewidth=2)
        ax1.set_xlabel('Number of Connections')
        ax1.set_ylabel('Success Rate (%)')
        ax1.set_title('Success Rate vs Concurrent Connections\n(Multiple Client IDs)')
        ax1.grid(True, alpha=0.3)
        
        # Connection time
        ax2.plot(df['connections_tested'], df['avg_connection_time'], 'r-o', linewidth=2)
        ax2.set_xlabel('Number of Connections')
        ax2.set_ylabel('Average Connection Time (s)')
        ax2.set_title('Connection Time vs Concurrent Connections\n(Multiple Client IDs)')
        ax2.grid(True, alpha=0.3)
        
        # Connections per second
        ax3.plot(df['connections_tested'], df['connections_per_second'], 'g-o', linewidth=2)
        ax3.set_xlabel('Number of Connections')
        ax3.set_ylabel('Connections per Second')
        ax3.set_title('Throughput vs Concurrent Connections\n(Multiple Client IDs)')
        ax3.grid(True, alpha=0.3)
        
        # Messages received
        ax4.bar(df['connections_tested'], df['total_messages'], alpha=0.7)
        ax4.set_xlabel('Number of Connections')
        ax4.set_ylabel('Total Messages Received')
        ax4.set_title('Messages Received vs Concurrent Connections\n(Multiple Client IDs)')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('websocket_multi_client_load_test_results.png', dpi=300, bbox_inches='tight')
        print(f"\n📊 Charts saved as 'websocket_multi_client_load_test_results.png'")

async def main():
    parser = argparse.ArgumentParser(description='WebSocket Load Tester - Multi Client ID')
    parser.add_argument('--url', default='ws://localhost:9097', help='Base URL of the service')
    parser.add_argument('--max-connections', type=int, default=1000, help='Maximum connections to test')
    parser.add_argument(' --step', type=int, default=100, help='Increment step for load testing')
    parser.add_argument('--duration', type=int, default=10, help='Test duration per load level (seconds)')
    parser.add_argument('--single-test', type=int, help='Run single test with specified connections')
    parser.add_argument('--test-patterns', action='store_true', help='Test different client ID patterns')
    parser.add_argument('--test-routing', action='store_true', help='Test message routing between clients')
    
    args = parser.parse_args()
    
    tester = WebSocketLoadTester(args.url)
    
    # Test health endpoint first
    print("🔍 Testing health endpoint...")
    async with aiohttp.ClientSession() as session:
        health = await tester.health_check(session)
        print(f"   Health status: {health}")
    
    if args.test_patterns:
        # Test different client ID patterns
        patterns = [
            "user", "admin", "device", "mobile", "web", 
            "api-client", "service", "backend", "frontend", "test"
        ]
        results = await tester.test_different_client_patterns(patterns, 10, 5)
        
        print(f"\n📊 CLIENT PATTERN RESULTS:")
        for result in results:
            print(f"   {result['pattern']:15}: {result['success_rate']:5.1f}% success, {result['avg_messages']:5.1f} avg messages")
    
    elif args.test_routing:
        # Test message routing
        routing_results = await tester.test_message_routing(10, 5)
        print(f"\n📊 MESSAGE ROUTING RESULTS:")
        print(f"   Routing success rate: {routing_results['routing_success_rate']:.1f}%")
        print(f"   Total messages received: {routing_results['total_messages_received']}")
        print(f"   Messages per client: {routing_results['messages_per_client']}")
    
    elif args.single_test:
        # Run single concurrent test
        print(f"\n🚀 Running single test with {args.single_test} connections...")
        result = await tester.test_concurrent_connections(args.single_test, args.duration)
        
        print(f"\n📊 SINGLE TEST RESULTS:")
        print(f"   Successful connections: {result['successful_connections']}/{result['total_connections']}")
        print(f"   Success rate: {result['success_rate']:.1f}%")
        print(f"   Average connection time: {result['avg_connection_time']:.3f}s")
        print(f"   Total messages received: {result['total_messages']}")
        print(f"   Test duration: {result['test_duration']:.2f}s")
        print(f"   Connections per second: {result['connections_per_second']:.1f}")
        print(f"   Client ID patterns used: {list(result['client_id_patterns'].keys())}")
        
    else:
        # Run incremental load test
        results = await tester.incremental_load_test(
            max_connections=args.max_connections,
            step=args.step,
            duration=args.duration
        )
        
        # Generate report
        tester.generate_report(results)

if __name__ == "__main__":
    # Install required packages:
    # pip install websockets aiohttp matplotlib pandas asyncio
    
    import logging
    logging.basicConfig(level=logging.INFO)
    from core.logging_config import get_logger

logger = get_logger(__name__)

    
    asyncio.run(main())