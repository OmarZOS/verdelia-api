# import pika
# import json
# import time
# import threading
# from datetime import datetime
# from functools import wraps



# import json
# from datetime import datetime, timedelta
# from typing import Dict, Any, Optional

# class NotificationBuilder:
#     """Base class for building notification parameters"""
    
#     @staticmethod
#     def build_params(**kwargs) -> str:
#         """Convert parameters to JSON string"""
#         return json.dumps(kwargs, ensure_ascii=False)
    
#     @staticmethod
#     def get_current_timestamp() -> str:
#         """Get current timestamp in ISO format"""
#         return datetime.now().isoformat()

# class OrderNotificationBuilder(NotificationBuilder):
#     """Builder for order-related notifications"""
    
#     @staticmethod
#     def order_received(order_id: int, order_number: str, amount: float, supplier_name: str, 
#                       customer_name: Optional[str] = None, items_count: Optional[int] = None) -> str:
#         """
#         New order received notification
        
#         Args:
#             order_id: Internal order ID
#             order_number: Human-readable order number (e.g., "ORD-7842")
#             amount: Order total amount
#             supplier_name: Name of the supplier/restaurant
#             customer_name: Name of the customer (optional)
#             items_count: Number of items in order (optional)
#         """
#         params = {
#             "order_id": order_id,
#             "order_number": order_number,
#             "amount": f"{amount:.2f}",
#             "supplier_name": supplier_name,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if customer_name:
#             params["customer_name"] = customer_name
#         if items_count:
#             params["items_count"] = items_count
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def order_status_changed(order_id: int, order_number: str, old_status: str, 
#                            new_status: str, supplier_name: str) -> str:
#         """Order status changed notification"""
#         return NotificationBuilder.build_params(
#             order_id=order_id,
#             order_number=order_number,
#             old_status=old_status,
#             new_status=new_status,
#             supplier_name=supplier_name,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )

# class InventoryNotificationBuilder(NotificationBuilder):
#     """Builder for inventory-related notifications"""
    
#     @staticmethod
#     def product_stock_critical(product_id: int, product_name: str, current_stock: int, 
#                               min_stock: int, supplier_name: str, unit: str = "units") -> str:
#         """
#         Product stock critically low notification
        
#         Args:
#             product_id: Internal product ID
#             product_name: Name of the product
#             current_stock: Current stock level
#             min_stock: Minimum required stock level
#             supplier_name: Name of the supplier/restaurant
#             unit: Unit of measurement (e.g., "units", "kg", "liters")
#         """
#         return NotificationBuilder.build_params(
#             product_id=product_id,
#             product_name=product_name,
#             current_stock=current_stock,
#             min_stock=min_stock,
#             supplier_name=supplier_name,
#             unit=unit,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def product_run_out(product_id: int, product_name: str, supplier_name: str, 
#                        last_restock: Optional[str] = None, unit: str = "units") -> str:
#         """
#         Product completely out of stock notification
#         """
#         params = {
#             "product_id": product_id,
#             "product_name": product_name,
#             "supplier_name": supplier_name,
#             "unit": unit,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if last_restock:
#             params["last_restock"] = last_restock
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def product_restocked(product_id: int, product_name: str, new_stock: int, 
#                          supplier_name: str, unit: str = "units") -> str:
#         """Product successfully restocked notification"""
#         return NotificationBuilder.build_params(
#             product_id=product_id,
#             product_name=product_name,
#             new_stock=new_stock,
#             supplier_name=supplier_name,
#             unit=unit,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )

# class SocialNotificationBuilder(NotificationBuilder):
#     """Builder for social interactions (reactions, comments)"""
    
#     @staticmethod
#     def reaction_received(user_id: int, user_name: str, target_type: str, 
#                          target_id: int, target_title: str, reaction_type: str = "liked") -> str:
#         """
#         Reaction received notification
        
#         Args:
#             user_id: ID of user who reacted
#             user_name: Name of user who reacted
#             target_type: Type of content (post, recipe, comment, etc.)
#             target_id: ID of the target content
#             target_title: Title/description of the target content
#             reaction_type: Type of reaction (liked, loved, etc.)
#         """
#         return NotificationBuilder.build_params(
#             user_id=user_id,
#             user_name=user_name,
#             target_type=target_type,
#             target_id=target_id,
#             target_title=target_title,
#             reaction_type=reaction_type,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def comment_received(user_id: int, user_name: str, target_type: str, 
#                         target_id: int, target_title: str, comment_preview: str,
#                         user_role: Optional[str] = None) -> str:
#         """
#         Comment received notification
#         """
#         params = {
#             "user_id": user_id,
#             "user_name": user_name,
#             "target_type": target_type,
#             "target_id": target_id,
#             "target_title": target_title,
#             "comment_preview": comment_preview[:100],  # Limit preview length
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if user_role:
#             params["user_role"] = user_role
            
#         return NotificationBuilder.build_params(**params)

# class RuleNotificationBuilder(NotificationBuilder):
#     """Builder for rule-related notifications"""
    
#     @staticmethod
#     def rule_expiry(rule_id: int, rule_name: str, days_left: int, 
#                    rule_type: str = "rule", supplier_name: Optional[str] = None) -> str:
#         """
#         Rule expiring soon notification
        
#         Args:
#             rule_id: Internal rule ID
#             rule_name: Name of the rule
#             days_left: Days until expiration (0 = expires today)
#             rule_type: Type of rule (discount, pricing, policy, etc.)
#             supplier_name: Name of the supplier (optional)
#         """
#         params = {
#             "rule_id": rule_id,
#             "rule_name": rule_name,
#             "days_left": days_left,
#             "rule_type": rule_type,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if supplier_name:
#             params["supplier_name"] = supplier_name
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def new_rule_added(rule_id: int, rule_name: str, rule_type: str, 
#                       added_by: str, supplier_name: Optional[str] = None) -> str:
#         """
#         New rule added notification
#         """
#         params = {
#             "rule_id": rule_id,
#             "rule_name": rule_name,
#             "rule_type": rule_type,
#             "added_by": added_by,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if supplier_name:
#             params["supplier_name"] = supplier_name
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def rule_activated(rule_id: int, rule_name: str, rule_type: str, 
#                       supplier_name: Optional[str] = None) -> str:
#         """Rule activated notification"""
#         params = {
#             "rule_id": rule_id,
#             "rule_name": rule_name,
#             "rule_type": rule_type,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if supplier_name:
#             params["supplier_name"] = supplier_name
            
#         return NotificationBuilder.build_params(**params)

# class PersonnelNotificationBuilder(NotificationBuilder):
#     """Builder for personnel and work-related notifications"""
    
#     @staticmethod
#     def work_invitation(organization_id: int, organization_name: str, role: str, 
#                        invited_by: str, invitation_id: Optional[int] = None) -> str:
#         """
#         Work invitation notification
        
#         Args:
#             organization_id: ID of the inviting organization
#             organization_name: Name of the organization
#             role: Role being offered (Manager, Chef, Staff, etc.)
#             invited_by: Name of person who sent invitation
#             invitation_id: Internal invitation ID (optional)
#         """
#         params = {
#             "organization_id": organization_id,
#             "organization_name": organization_name,
#             "role": role,
#             "invited_by": invited_by,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if invitation_id:
#             params["invitation_id"] = invitation_id
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def invitation_accepted(user_id: int, user_name: str, organization_name: str, 
#                            role: str) -> str:
#         """Work invitation accepted notification"""
#         return NotificationBuilder.build_params(
#             user_id=user_id,
#             user_name=user_name,
#             organization_name=organization_name,
#             role=role,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def invitation_declined(user_id: int, user_name: str, organization_name: str) -> str:
#         """Work invitation declined notification"""
#         return NotificationBuilder.build_params(
#             user_id=user_id,
#             user_name=user_name,
#             organization_name=organization_name,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def role_changed(user_id: int, user_name: str, old_role: str, 
#                     new_role: str, organization_name: str) -> str:
#         """User role changed notification"""
#         return NotificationBuilder.build_params(
#             user_id=user_id,
#             user_name=user_name,
#             old_role=old_role,
#             new_role=new_role,
#             organization_name=organization_name,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )

# class RecipeNotificationBuilder(NotificationBuilder):
#     """Builder for recipe-related notifications"""
    
#     @staticmethod
#     def recipe_reaction(user_id: int, user_name: str, recipe_id: int, 
#                        recipe_name: str, reaction_type: str = "liked") -> str:
#         """
#         Recipe reaction received notification
#         """
#         return NotificationBuilder.build_params(
#             user_id=user_id,
#             user_name=user_name,
#             recipe_id=recipe_id,
#             recipe_name=recipe_name,
#             reaction_type=reaction_type,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def recipe_comment(user_id: int, user_name: str, recipe_id: int, 
#                       recipe_name: str, comment_preview: str,
#                       user_role: Optional[str] = None) -> str:
#         """
#         Recipe comment received notification
#         """
#         params = {
#             "user_id": user_id,
#             "user_name": user_name,
#             "recipe_id": recipe_id,
#             "recipe_name": recipe_name,
#             "comment_preview": comment_preview[:100],
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if user_role:
#             params["user_role"] = user_role
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def recipe_published(recipe_id: int, recipe_name: str, published_by: str) -> str:
#         """Recipe published notification"""
#         return NotificationBuilder.build_params(
#             recipe_id=recipe_id,
#             recipe_name=recipe_name,
#             published_by=published_by,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )

# class SystemNotificationBuilder(NotificationBuilder):
#     """Builder for system and administrative notifications"""
    
#     @staticmethod
#     def system_update(version: str, new_features: list, update_type: str = "minor") -> str:
#         """
#         System update notification
#         """
#         return NotificationBuilder.build_params(
#             version=version,
#             new_features=new_features,
#             update_type=update_type,
#             timestamp=NotificationBuilder.get_current_timestamp()
#         )
    
#     @staticmethod
#     def maintenance_scheduled(start_time: str, end_time: str, 
#                              reason: Optional[str] = None) -> str:
#         """System maintenance scheduled notification"""
#         params = {
#             "start_time": start_time,
#             "end_time": end_time,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if reason:
#             params["reason"] = reason
            
#         return NotificationBuilder.build_params(**params)
    
#     @staticmethod
#     def new_feature_available(feature_name: str, feature_description: str, 
#                              available_from: Optional[str] = None) -> str:
#         """New feature available notification"""
#         params = {
#             "feature_name": feature_name,
#             "feature_description": feature_description,
#             "timestamp": NotificationBuilder.get_current_timestamp()
#         }
        
#         if available_from:
#             params["available_from"] = available_from
            
#         return NotificationBuilder.build_params(**params)

# # Main facade class for easy access
# class NotificationFactory:
#     """Facade class to provide easy access to all notification builders"""
    
#     # Order notifications
#     order = OrderNotificationBuilder
#     # Inventory notifications  
#     inventory = InventoryNotificationBuilder
#     # Social notifications
#     social = SocialNotificationBuilder
#     # Rule notifications
#     rule = RuleNotificationBuilder
#     # Personnel notifications
#     personnel = PersonnelNotificationBuilder
#     # Recipe notifications
#     recipe = RecipeNotificationBuilder
#     # System notifications
#     system = SystemNotificationBuilder

# class FlutterNotificationProducer:
#     def __init__(self, rabbitmq_url: str = "amqp://dev_user:dev_pass@localhost:5672/verdelia"):
#         params = pika.ConnectionParameters(
#                 host='localhost',
#                 port=5672,
#                 virtual_host='/verdelia',  # or your custom vhost
#                 credentials=pika.PlainCredentials('dev_user', 'dev_pass')
#             )

#         self.connection = pika.BlockingConnection(params)


#         self.channel = self.connection.channel()
        
#         # Create user-specific queues for direct messaging
#         self._setup_user_queues()
    
#     def _setup_user_queues(self):
#         """Setup exchanges and user-specific queues"""
#         # Direct exchange for user-specific notifications
#         self.channel.exchange_declare(
#             exchange='user_notifications',
#             exchange_type='direct',
#             durable=True
#         )
        
#         # Fanout exchange for broadcast notifications
#         self.channel.exchange_declare(
#             exchange='broadcast_notifications', 
#             exchange_type='fanout',
#             durable=True
#         )
    
#     def send_to_user(self, user_id: int, notification_code: str, **params):
#         """Send notification to a specific user's queue"""
#         message = {
#             'type': 'user_notification',
#             'user_id': user_id,
#             'notification_code': notification_code,
#             'data': params,
#             'timestamp': datetime.utcnow().isoformat(),
#             'preformatted': self._preformat_notification(notification_code, params)
#         }
        
#         self.channel.basic_publish(
#             exchange='user_notifications',
#             routing_key=f'user_{user_id}',  # User-specific routing key
#             body=json.dumps(message),
#             properties=pika.BasicProperties(
#                 delivery_mode=2,  # Persistent
#                 content_type='application/json',
#                 headers={
#                     'notification_type': notification_code,
#                     'user_id': str(user_id)
#                 }
#             )
#         )
#         print(f" [→] Sent {notification_code} to user_{user_id}")
    
#     def send_to_supplier(self, supplier_id: int, notification_code: str, **params):
#         """Send notification to all users of a supplier"""
#         message = {
#             'type': 'supplier_notification',
#             'supplier_id': supplier_id,
#             'notification_code': notification_code,
#             'data': params,
#             'timestamp': datetime.utcnow().isoformat(),
#             'preformatted': self._preformat_notification(notification_code, params)
#         }
        
#         self.channel.basic_publish(
#             exchange='broadcast_notifications',
#             routing_key='',  # Fanout doesn't use routing key
#             body=json.dumps(message),
#             properties=pika.BasicProperties(
#                 delivery_mode=2,
#                 content_type='application/json'
#             )
#         )
#         print(f" [→] Broadcast {notification_code} to supplier_{supplier_id}")
    
#     def _preformat_notification(self, notification_code: str, params: dict) -> dict:
#         """Pre-format notification for Flutter app"""
#         # Use your existing notification builder
#         params_json = NotificationFactory.order.order_received(**params) if notification_code == 'order_received' else json.dumps(params)
        
#         return {
#             'title': self._get_notification_title(notification_code, params),
#             'body': self._get_notification_body(notification_code, params),
#             'action': self._get_notification_action(notification_code),
#             'icon': self._get_notification_icon(notification_code),
#             'color': self._get_notification_color(notification_code),
#             'route': self._get_notification_route(notification_code, params)
#         }
    
#     def _get_notification_title(self, code: str, params: dict) -> str:
#         titles = {
#             'order_received': 'New Order 📦',
#             'product_stock_critical': 'Low Stock Alert ⚠️',
#             'product_run_out': 'Out of Stock 🚫',
#             'work_invitation': 'Work Invitation 👥',
#             'rule_expiry': 'Rule Expiring Soon ⏰'
#         }
#         return titles.get(code, 'New Notification')
    
#     def _get_notification_body(self, code: str, params: dict) -> str:
#         # Use your existing formatting logic
#         if code == 'order_received':
#             return f"Order #{params.get('order_number', '')} for ${params.get('amount', 0)}"
#         elif code == 'product_stock_critical':
#             return f"Low stock: {params.get('product_name')} ({params.get('current_stock')} left)"
#         # Add more cases...
#         return "You have a new notification"
    
#     def _get_notification_action(self, code: str) -> str:
#         actions = {
#             'order_received': 'View Order',
#             'product_stock_critical': 'Check Stock',
#             'work_invitation': 'Respond'
#         }
#         return actions.get(code, 'View')
    
#     def _get_notification_icon(self, code: str) -> str:
#         icons = {
#             'order_received': '📦',
#             'product_stock_critical': '⚠️',
#             'product_run_out': '🚫',
#             'work_invitation': '👥',
#             'rule_expiry': '⏰'
#         }
#         return icons.get(code, '🔔')
    
#     def _get_notification_color(self, code: str) -> str:
#         colors = {
#             'order_received': '#4CAF50',
#             'product_stock_critical': '#FF9800', 
#             'product_run_out': '#F44336',
#             'work_invitation': '#9C27B0'
#         }
#         return colors.get(code, '#607D8B')
    
#     def _get_notification_route(self, code: str, params: dict) -> str:
#         routes = {
#             'order_received': '/orders/${order_id}',
#             'product_stock_critical': '/inventory',
#             'work_invitation': '/invitations'
#         }
#         return routes.get(code, '/notifications')
    
#     def close(self):
#         self.connection.close()

# # Usage in your API endpoints


# def rabbitmq_connection_manager(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         producer = None
#         try:
#             # Instantiate the producer
#             producer = FlutterNotificationProducer()
#             # Pass the producer as a keyword argument
#             kwargs['producer'] = producer
#             return func(*args, **kwargs)
#         finally:
#             # Ensure the connection is closed
#             if producer:
#                 producer.close()
#     return wrapper


# @rabbitmq_connection_manager
# def notify_order_received(order_data: dict, user_id: int, producer=None):
#     # Use the passed producer
#     producer.send_to_user(
#         user_id=user_id,
#         notification_code='order_received',
#         order_id=order_data['id'],
#         order_number=order_data['number'],
#         amount=order_data['amount'],
#         supplier_name=order_data['supplier_name']
#     )



# class RabbitMQTester:
#     def __init__(self, rabbitmq_url: str = "amqp://localhost:5672"):
#         self.rabbitmq_url = rabbitmq_url
#         self.consumer_messages = []
#         self.test_results = {}
    
#     def test_connection(self):
#         """Test basic RabbitMQ connection"""
#         try:
#             params = pika.ConnectionParameters(
#                 host='localhost',
#                 port=5672,
#                 virtual_host='/verdelia',  # or your custom vhost
#                 credentials=pika.PlainCredentials('dev_user', 'dev_pass')
#             )

#             connection = pika.BlockingConnection(params)
#             # connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
#             channel = connection.channel()
#             connection.close()
#             return True, "✅ Connection successful"
#         except Exception as e:
#             return False, f"❌ Connection failed: {e}"
    
#     def setup_test_queues(self):
#         """Setup test queues and exchanges"""
#         try:
#             params = pika.ConnectionParameters(
#                 host='localhost',
#                 port=5672,
#                 virtual_host='/verdelia',  # or your custom vhost
#                 credentials=pika.PlainCredentials('dev_user', 'dev_pass')
#             )

#             connection = pika.BlockingConnection(params)
#             channel = connection.channel()
            
#             # Declare test exchanges
#             channel.exchange_declare(exchange='user_notifications', exchange_type='direct', durable=True)
#             channel.exchange_declare(exchange='broadcast_notifications', exchange_type='fanout', durable=True)
            
#             # Declare test queues
#             channel.queue_declare(queue='test_user_1', durable=True)
#             channel.queue_declare(queue='test_user_2', durable=True)
#             channel.queue_declare(queue='test_broadcast', durable=True)
            
#             # Bind queues
#             channel.queue_bind(exchange='user_notifications', queue='test_user_1', routing_key='user_1')
#             channel.queue_bind(exchange='user_notifications', queue='test_user_2', routing_key='user_2')
#             channel.queue_bind(exchange='broadcast_notifications', queue='test_broadcast', routing_key='')
            
#             connection.close()
#             return True, "✅ Test queues setup successful"
#         except Exception as e:
#             return False, f"❌ Queue setup failed: {e}"
    
#     def start_test_consumer(self, queue_name: str, user_id: int = None):
#         """Start a consumer to listen for test messages"""
#         def consume_messages():
#             try:
#                 params = pika.ConnectionParameters(
#                     host='localhost',
#                     port=5672,
#                     virtual_host='/verdelia',  # or your custom vhost
#                     credentials=pika.PlainCredentials('dev_user', 'dev_pass')
#                 )

#                 connection = pika.BlockingConnection(params)
#                 channel = connection.channel()
                
#                 def callback(ch, method, properties, body):
#                     message = json.loads(body)
#                     self.consumer_messages.append({
#                         'queue': queue_name,
#                         'user_id': user_id,
#                         'message': message,
#                         'timestamp': datetime.now().isoformat()
#                     })
#                     print(f"📨 [Consumer {queue_name}] Received: {message['notification_code']}")
#                     ch.basic_ack(delivery_tag=method.delivery_tag)
                
#                 channel.basic_consume(
#                     queue=queue_name,
#                     on_message_callback=callback,
#                     auto_ack=False
#                 )
                
#                 print(f"👂 [Consumer {queue_name}] Started listening...")
#                 channel.start_consuming()
                
#             except Exception as e:
#                 print(f"❌ Consumer error: {e}")
        
#         consumer_thread = threading.Thread(target=consume_messages, daemon=True)
#         consumer_thread.start()
#         return consumer_thread
    
#     def test_send_to_user(self):
#         """Test sending notification to specific user"""
#         try:
#             producer = FlutterNotificationProducer(self.rabbitmq_url)
            
#             # Test data
#             test_data = {
#                 'id': 12345,
#                 'number': 'ORD-7842',
#                 'amount': 250.50,
#                 'supplier_name': 'Test Restaurant'
#             }
            
#             producer.send_to_user(
#                 user_id=1,
#                 notification_code='order_received',
#                 **test_data
#             )
            
#             producer.close()
            
#             # Wait for message to be delivered
#             time.sleep(2)
            
#             # Check if message was received
#             user_messages = [msg for msg in self.consumer_messages if msg['user_id'] == 1]
            
#             if user_messages:
#                 return True, f"✅ User notification sent and received: {user_messages[-1]['message']['notification_code']}"
#             else:
#                 return False, "❌ User notification not received"
                
#         except Exception as e:
#             return False, f"❌ User notification test failed: {e}"
    
#     def test_send_to_supplier(self):
#         """Test broadcasting notification to supplier"""
#         try:
#             producer = FlutterNotificationProducer(self.rabbitmq_url)
            
#             # Test data
#             test_data = {
#                 'product_id': 101,
#                 'product_name': 'Test Product',
#                 'current_stock': 5,
#                 'min_stock': 10,
#                 'supplier_name': 'Test Supplier'
#             }
            
#             producer.send_to_supplier(
#                 supplier_id=1,
#                 notification_code='product_stock_critical',
#                 **test_data
#             )
            
#             producer.close()
            
#             # Wait for message to be delivered
#             time.sleep(2)
            
#             # Check if broadcast message was received
#             broadcast_messages = [msg for msg in self.consumer_messages if msg['queue'] == 'test_broadcast']
            
#             if broadcast_messages:
#                 return True, f"✅ Supplier broadcast sent and received: {broadcast_messages[-1]['message']['notification_code']}"
#             else:
#                 return False, "❌ Supplier broadcast not received"
                
#         except Exception as e:
#             return False, f"❌ Supplier broadcast test failed: {e}"
    
#     def test_all_notification_types(self):
#         """Test all notification types"""
#         test_cases = [
#             {
#                 'name': 'order_received',
#                 'user_id': 1,
#                 'code': 'order_received',
#                 'data': {
#                     'id': 1001, 'number': 'TEST-001', 'amount': 100.00, 
#                     'supplier_name': 'Test Restaurant', 'customer_name': 'Test Customer'
#                 }
#             },
#             {
#                 'name': 'product_stock_critical', 
#                 'user_id': 2,
#                 'code': 'product_stock_critical',
#                 'data': {
#                     'product_id': 2001, 'product_name': 'Test Product', 'current_stock': 3,
#                     'min_stock': 10, 'supplier_name': 'Test Supplier', 'unit': 'units'
#                 }
#             },
#             {
#                 'name': 'work_invitation',
#                 'user_id': 1, 
#                 'code': 'work_invitation',
#                 'data': {
#                     'organization_id': 3001, 'organization_name': 'Test Organization',
#                     'role': 'Manager', 'invited_by': 'Test Admin'
#                 }
#             },
#             {
#                 'name': 'rule_expiry',
#                 'user_id': 2,
#                 'code': 'rule_expiry', 
#                 'data': {
#                     'rule_id': 4001, 'rule_name': 'Test Rule', 'days_left': 2,
#                     'rule_type': 'discount', 'supplier_name': 'Test Supplier'
#                 }
#             }
#         ]
        
#         results = {}
        
#         try:
#             producer = FlutterNotificationProducer(self.rabbitmq_url)
            
#             for test_case in test_cases:
#                 try:
#                     if test_case['code'] == 'order_received':
#                         producer.send_to_user(
#                             user_id=test_case['user_id'],
#                             notification_code=test_case['code'],
#                             **test_case['data']
#                         )
#                     elif test_case['code'] == 'product_stock_critical':
#                         producer.send_to_supplier(
#                             supplier_id=1,
#                             notification_code=test_case['code'],
#                             **test_case['data']
#                         )
#                     else:
#                         producer.send_to_user(
#                             user_id=test_case['user_id'],
#                             notification_code=test_case['code'],
#                             **test_case['data']
#                         )
                    
#                     results[test_case['name']] = f"✅ Sent successfully"
#                     print(f"✅ Sent {test_case['name']}")
                    
#                 except Exception as e:
#                     results[test_case['name']] = f"❌ Failed: {e}"
#                     print(f"❌ Failed {test_case['name']}: {e}")
            
#             producer.close()
            
#             # Wait for all messages
#             time.sleep(3)
            
#             # Verify received messages
#             for test_case in test_cases:
#                 relevant_messages = [
#                     msg for msg in self.consumer_messages 
#                     if msg['message']['notification_code'] == test_case['code']
#                 ]
#                 if relevant_messages:
#                     results[test_case['name']] += f" | 📨 Received"
#                 else:
#                     results[test_case['name']] += f" | ❌ Not received"
            
#             return True, results
            
#         except Exception as e:
#             return False, f"❌ Comprehensive test failed: {e}"
    
#     def test_decorator_function(self):
#         """Test the rabbitmq_connection_manager decorator"""
#         try:
#             # Test data
#             order_data = {
#                 'id': 99999,
#                 'number': 'DECORATOR-TEST',
#                 'amount': 99.99,
#                 'supplier_name': 'Decorator Test Restaurant'
#             }
            
#             # This should use the decorator
#             try:
#                 notify_order_received(order_data, user_id=1)
#             except :
#                 pass
            
#             # Wait for message
#             time.sleep(2)
            
#             # Check if message was received
#             decorator_messages = [
#                 msg for msg in self.consumer_messages 
#                 if msg['message']['data'].get('order_number') == 'DECORATOR-TEST'
#             ]
            
#             if decorator_messages:
#                 return True, "✅ Decorator function test passed"
#             else:
#                 return False, "❌ Decorator function test failed - message not received"
                
#         except Exception as e:
#             return False, f"❌ Decorator function test failed: {e}"
    
#     def run_comprehensive_test(self):
#         """Run all tests"""
#         print("🚀 Starting Comprehensive RabbitMQ Producer Tests")
#         print("=" * 50)
        
#         # Start consumers for testing
#         print("👂 Starting test consumers...")
#         self.start_test_consumer('test_user_1', user_id=1)
#         self.start_test_consumer('test_user_2', user_id=2) 
#         self.start_test_consumer('test_broadcast')
        
#         time.sleep(2)  # Give consumers time to start
        
#         test_functions = [
#             ("Connection Test", self.test_connection),
#             ("Queue Setup Test", self.setup_test_queues),
#             ("User Notification Test", self.test_send_to_user),
#             ("Supplier Broadcast Test", self.test_send_to_supplier),
#             ("Decorator Function Test", self.test_decorator_function),
#             ("All Notification Types Test", self.test_all_notification_types)
#         ]
        
#         all_passed = True
#         results = {}
        
#         for test_name, test_func in test_functions:
#             print(f"\n🧪 Running {test_name}...")
#             success, message = test_func()
#             results[test_name] = {'success': success, 'message': message}
            
#             if success:
#                 print(f"✅ {test_name}: PASSED")
#                 if isinstance(message, dict):
#                     for key, value in message.items():
#                         print(f"   - {key}: {value}")
#                 else:
#                     print(f"   - {message}")
#             else:
#                 print(f"❌ {test_name}: FAILED")
#                 print(f"   - {message}")
#                 all_passed = False
        
#         print("\n" + "=" * 50)
#         print("📊 TEST SUMMARY")
#         print("=" * 50)
        
#         for test_name, result in results.items():
#             status = "✅ PASS" if result['success'] else "❌ FAIL"
#             print(f"{status} {test_name}")
        
#         print(f"\n📨 Total messages received: {len(self.consumer_messages)}")
#         for msg in self.consumer_messages:
#             print(f"   - {msg['queue']}: {msg['message']['notification_code']}")
        
#         if all_passed:
#             print("\n🎉 ALL TESTS PASSED! RabbitMQ producer is working correctly.")
#         else:
#             print("\n💥 SOME TESTS FAILED! Check the errors above.")
        
#         return all_passed, results

# def quick_test():
#     """Quick test function for immediate verification"""
#     print("⚡ Running Quick RabbitMQ Test")
    
#     tester = RabbitMQTester()
    
#     # Basic connection test
#     success, message = tester.test_connection()
#     print(f"Connection: {message}")
    
#     if success:
#         # Test single message
#         try:
#             producer = FlutterNotificationProducer()
#             producer.send_to_user(
#                 user_id=1,
#                 notification_code='order_received',
#                 id=999,
#                 number='QUICK-TEST',
#                 amount=50.00,
#                 supplier_name='Quick Test Restaurant'
#             )
#             producer.close()
#             print("✅ Quick test message sent successfully!")
#             print("💡 Check RabbitMQ management UI at http://localhost:15672")
#             print("   Username: guest, Password: guest")
#         except Exception as e:
#             print(f"❌ Quick test failed: {e}")
#     else:
#         print("💡 Make sure RabbitMQ is running:")
#         print("   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")

# if __name__ == "__main__":
#     import sys
    
#     if len(sys.argv) > 1 and sys.argv[1] == "quick":
#         quick_test()
#     else:
#         tester = RabbitMQTester()
#         tester.run_comprehensive_test()