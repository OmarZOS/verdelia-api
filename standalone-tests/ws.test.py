#!/usr/bin/env python3
"""
WebSocket Listener for User 4 Notifications
Run this script to listen for real-time notifications
"""

import asyncio
import json
import websockets
import sys
from datetime import datetime

async def listen_for_notifications(user_id: int = 4, duration: int = 0):
    """
    Listen for notifications for a specific user
    
    Args:
        user_id: User ID to listen for
        duration: Duration in seconds (0 = infinite, press Ctrl+C to stop)
    """
    ws_url = f"ws://localhost:9097/stream/ws/{user_id}"
    
    print("=" * 60)
    print(f"🔔 WEBSOCKET NOTIFICATION LISTENER")
    print("=" * 60)
    print(f"📱 User ID: {user_id}")
    print(f"🌐 WebSocket URL: {ws_url}")
    print(f"⏱️  Duration: {'Infinite (Ctrl+C to stop)' if duration == 0 else f'{duration} seconds'}")
    print("=" * 60)
    
    message_count = 0
    start_time = datetime.now()
    try:
        async with websockets.connect(ws_url) as websocket:
            # Get connection confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            conn_data = json.loads(response)
            print(f"\n✅ Connected successfully!")
            print(f"   Queue: {conn_data.get('queue')}")
            print(f"   Client ID: {conn_data.get('client_id')}")
            print(f"   Status: Listening for notifications...\n")
            print("-" * 60)
            
            
            # Calculate end time if duration is specified
            end_time = None if duration == 0 else start_time.timestamp() + duration
            
            while True:
                try:
                    # Set timeout based on duration
                    timeout = 1.0
                    if end_time:
                        remaining = end_time - datetime.now().timestamp()
                        if remaining <= 0:
                            break
                        timeout = min(1.0, remaining)
                    
                    message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    data = json.loads(message)
                    message_count += 1
                    
                    # Format the received message nicely
                    print(f"\n📨 [{message_count}] Received at {datetime.now().strftime('%H:%M:%S')}")
                    print(f"   Type: {data.get('type', 'unknown')}")
                    print(f"   Data: {data}")
                    if 'notification_code' in data:
                        print(f"   Code: {data['notification_code']}")
                    
                    if 'data' in data:
                        print(f"   Title: {data['data'].get('title', 'N/A')}")
                        print(f"   Body: {data['data'].get('body', 'N/A')}")
                    
                    # Print full message for debugging (optional)
                    # print(f"   Full: {json.dumps(data, indent=6)}")
                    
                    print("-" * 60)
                    
                except asyncio.TimeoutError:
                    # No message received in this interval
                    if end_time:
                        continue
                    # Print a dot every 2 seconds to show we're alive
                    if int(datetime.now().timestamp()) % 2 == 0:
                        print(".", end="", flush=True)
                    continue
                    
    except websockets.exceptions.ConnectionClosed:
        print("\n❌ Connection closed by server")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Print summary
    elapsed = (datetime.now() - start_time).seconds
    print("\n" + "=" * 60)
    print(f"📊 LISTENING SUMMARY")
    print("=" * 60)
    print(f"   Duration: {elapsed} seconds")
    print(f"   Messages received: {message_count}")
    
    if message_count > 0:
        print(f"\n✅ Successfully received {message_count} notification(s)!")
    else:
        print("\n⚠️  No notifications received.")
        print("\n   To send a test notification, run in another terminal:")
        print("   python send_notification.py 4 'Hello World'")
    
    print("=" * 60)


async def send_test_notification(user_id: int = 4, message: str = "Test notification"):
    """Send a test notification via RabbitMQ"""
    try:
        import pika
        
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                virtual_host='/verdelia',
                credentials=pika.PlainCredentials('dev_user', 'dev_pass')
            )
        )
        channel = connection.channel()
        
        notification = {
            'type': 'user_notification',
            'user_id': user_id,
            'notification_code': 'test_notification',
            'data': {
                'title': 'Test Notification',
                'body': message,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        channel.basic_publish(
            exchange='user_notifications',
            routing_key=f'user.{user_id}',
            body=json.dumps(notification),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        
        print(f"✅ Test notification sent to user {user_id}")
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False


async def interactive_mode():
    """Interactive mode - send messages while listening"""
    print("\n🔄 INTERACTIVE MODE")
    print("Type a message and press Enter to send (or 'quit' to exit)")
    print("-" * 40)
    
    while True:
        message = input("\n📝 Message: ")
        if message.lower() in ['quit', 'exit', 'q']:
            break
        await send_test_notification(4, message)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Notification Listener")
    parser.add_argument("--user", "-u", type=int, default=4, help="User ID to listen for")
    parser.add_argument("--duration", "-d", type=int, default=0, help="Duration in seconds (0 = infinite)")
    parser.add_argument("--send", "-s", type=str, help="Send a test notification and exit")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode (send messages while listening)")
    
    args = parser.parse_args()
    
    if args.send:
        # Just send a message
        asyncio.run(send_test_notification(args.user, args.send))
    elif args.interactive:
        # Interactive mode - not implemented fully, use two terminals
        print("For interactive mode, run two terminals:")
        print("  Terminal 1: python listener.py --user 4")
        print("  Terminal 2: python listener.py --user 4 --send 'Your message'")
    else:
        # Listen for notifications
        try:
            asyncio.run(listen_for_notifications(args.user, args.duration))
        except KeyboardInterrupt:
            print("\n\n👋 Listener stopped by user")
            sys.exit(0)