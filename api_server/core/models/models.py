from sqlalchemy import BigInteger, Column, DECIMAL, Date, DateTime, Enum, Float, ForeignKeyConstraint, Index, Integer, JSON, String, TIMESTAMP, Table, Text, text
from sqlalchemy.dialects.mysql import TINYINT

from core.models.persistent_models import Location,Base, metadata
from geoalchemy2.types import Geometry
from sqlalchemy.orm import declarative_base, relationship


class Address(Base):
    __tablename__ = 'address'

    id_address = Column(Integer, primary_key=True)
    address_street = Column(String(45))
    address_city = Column(String(45))
    address_postal_code = Column(String(45))
    address_country = Column(String(45))

    location = relationship('Location', back_populates='location_address')
    delivery = relationship('Delivery', foreign_keys='[Delivery.delivery_address_id]', back_populates='delivery_address')
    delivery_ = relationship('Delivery', foreign_keys='[Delivery.delivery_current_address_id]', back_populates='delivery_current_address')


class AppUser(Base):
    __tablename__ = 'app_user'
    __table_args__ = (
        ForeignKeyConstraint(['app_user_person_id'], ['person.id_person'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_app_user_3'),
        ForeignKeyConstraint(['app_user_subscription_ref'], ['subscription.id_subscription'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_app_user_2'),
        ForeignKeyConstraint(['app_user_wallet_id'], ['wallet.id_wallet'], name='fk_app_user_4'),
        Index('fk_app_user_2_idx', 'app_user_subscription_ref'),
        Index('fk_app_user_3_idx', 'app_user_person_id'),
        Index('fk_app_user_4_idx', 'app_user_wallet_id')
    )

    id_app_user = Column(Integer, primary_key=True)
    app_user_name = Column(String(100))
    app_user_password = Column(String(256))
    app_user_person_id = Column(Integer)
    app_user_type = Column(Enum('admin', 'provider', 'customer', 'patient', 'guest'), server_default=text("'customer'"))
    app_user_preferences = Column(Text)
    app_user_image_url = Column(String(255))
    app_user_last_active = Column(TIMESTAMP)
    app_user_last_updated = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    app_user_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    app_user_subscription_ref = Column(Integer)
    app_user_email = Column(String(255))
    app_user_wallet_id = Column(Integer)
    app_user_login_option = Column(Enum('google', 'verdelia'))
    verified_app_user = Column(TINYINT)
    user_quota = Column(Integer, server_default=text("'0'"))

    app_user_person = relationship('Person', back_populates='app_user')
    subscription = relationship('Subscription', back_populates='app_user')
    app_user_wallet = relationship('Wallet', back_populates='app_user')
    naming_contribution = relationship('NamingContribution', back_populates='app_user')
    comment = relationship('Comment', back_populates='app_user')
    discount = relationship('Discount', back_populates='discount_user')
    ingredient = relationship('Ingredient', back_populates='ingredient_user')
    notification = relationship('Notification', back_populates='app_user')
    provider_organisation = relationship('ProviderOrganisation', back_populates='app_user')
    report = relationship('Report', back_populates='app_user')
    comment_reaction = relationship('CommentReaction', back_populates='app_user')
    placed_order = relationship('PlacedOrder', back_populates='ordering_user')
    product_provider = relationship('ProductProvider', back_populates='app_user')
    recipe = relationship('Recipe', back_populates='recipe_owner')
    additional_fee = relationship('AdditionalFee', back_populates='additional_fee_user')
    cart = relationship('Cart', foreign_keys='[Cart.cart_client_user]', back_populates='app_user')
    cart_ = relationship('Cart', foreign_keys='[Cart.cart_selling_user]', back_populates='app_user_')
    conversation = relationship('Conversation', foreign_keys='[Conversation.conversation_destination_user_id]', back_populates='conversation_destination_user')
    conversation_ = relationship('Conversation', foreign_keys='[Conversation.conversation_sender_user_id]', back_populates='conversation_sender_user')
    management_rule = relationship('ManagementRule', back_populates='app_user')
    product = relationship('Product', back_populates='app_user')
    provider_reaction = relationship('ProviderReaction', back_populates='app_user')
    recipe_reaction = relationship('RecipeReaction', back_populates='app_user')
    product_reaction = relationship('ProductReaction', back_populates='app_user')
    role_invitation = relationship('RoleInvitation', back_populates='app_user')
    service_contribution = relationship('ServiceContribution', back_populates='app_user')


class CareGiver(Base):
    __tablename__ = 'care_giver'
    __table_args__ = (
        ForeignKeyConstraint(['staff_role_id'], ['staff_role.id_staff_role'], name='fk_care_giver_staff_role1'),
        Index('fk_doctor_staff_role1_idx', 'staff_role_id')
    )

    id_care_giver = Column(Integer, primary_key=True)
    staff_role_id = Column(Integer)
    verified_care_giver = Column(TINYINT)
    care_giver_license = Column(String(255))
    care_giver_type = Column(Enum('DOCTOR', 'PHARMACIST', 'PHYSICIAN', 'DIETITIAN', 'PHYSICAL_THERAPIST', 'NURSE'))

    staff_role = relationship('StaffRole', back_populates='care_giver')
    person = relationship('Person', back_populates='doctor')
    diagnosis = relationship('Diagnosis', back_populates='doctor')


class Invoice(Base):
    __tablename__ = 'invoice'
    __table_args__ = (
        Index('idx_invoice_status', 'invoice_status'),
    )

    invoice_id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100))
    invoice_total_amount = Column(DECIMAL(15, 4))
    invoice_status = Column(Enum('unpaid', 'paid', 'canceled', 'partially_paid', 'overdue', 'refunded'), server_default=text("'unpaid'"), comment='unpaid, paid, canceled')
    invoice_issue_date = Column(Date)
    invoice_due_date = Column(Date)
    invoice_notes = Column(Text)
    invoice_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    invoice_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    invoice_type = Column(Enum('receipt', 'invoice', 'proforma'), server_default=text("'receipt'"))
    invoice_tax_applied = Column(TINYINT)

    payment = relationship('Payment', back_populates='payment_invoice')
    placed_order = relationship('PlacedOrder', back_populates='invoice')
    additional_fee = relationship('AdditionalFee', back_populates='invoice')
    cart = relationship('Cart', back_populates='invoice')
    delivery = relationship('Delivery', back_populates='invoice')


class NamingContribution(Base):
    __tablename__ = 'naming_contribution'
    __table_args__ = (
        ForeignKeyConstraint(['naming_contribution_by'], ['app_user.id_app_user'], name='fk_naming_contribution_1'),
        Index('fk_naming_contribution_1_idx', 'naming_contribution_by')
    )

    id_naming_contribution = Column(Integer, primary_key=True)
    naming_contribution_ar = Column(String(255))
    naming_contribution_fr = Column(String(255))
    naming_contribution_en = Column(String(255))
    naming_contribution_status = Column(Enum('PENDING', 'ACCEPTED', 'APP_TRANSLATED', 'REJECTED'), server_default=text("'PENDING'"))
    naming_contribution_icon_url = Column(String(255))
    naming_contribution_by = Column(Integer)
    naming_contribution_app_version = Column(String(45))
    naming_contribution_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    naming_contribution_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    naming_contribution_type = Column(Enum('product', 'provider', 'ingredient', 'recipe', 'service', 'symptom', 'role'))

    app_user = relationship('AppUser', back_populates='naming_contribution')
    provided_service_category = relationship('ProvidedServiceCategory', back_populates='naming_contribution')
    staff_role = relationship('StaffRole', back_populates='naming_contribution')
    ingredient = relationship('Ingredient', back_populates='naming_contribution')
    product_category = relationship('ProductCategory', back_populates='naming_contribution')
    product_provider_type = relationship('ProductProviderType', back_populates='naming_contribution')
    provider_details = relationship('ProviderDetails', back_populates='naming_contribution')
    provider_organisation = relationship('ProviderOrganisation', back_populates='naming_contribution')
    recipe_category = relationship('RecipeCategory', back_populates='naming_contribution')
    symptom = relationship('Symptom', back_populates='naming_contribution')
    iproduct = relationship('Iproduct', back_populates='naming_contribution')


class Person(Base):
    __tablename__ = 'person'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['care_giver.id_care_giver'], name='fk_person_doctor1'),
        ForeignKeyConstraint(['person_details_id'], ['person_details.id_person_details'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_person_1'),
        ForeignKeyConstraint(['person_location_id'], ['location.id_location'], name='fk_person_3'),
        Index('fk_person_1_idx', 'person_details_id'),
        Index('fk_person_3_idx', 'person_location_id'),
        Index('fk_person_doctor1_idx', 'doctor_id')
    )

    id_person = Column(Integer, primary_key=True)
    person_details_id = Column(Integer)
    person_blood_type = Column(Enum('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'))
    person_location_id = Column(Integer)
    doctor_id = Column(Integer)

    app_user = relationship('AppUser', back_populates='app_user_person')
    doctor = relationship('CareGiver', back_populates='person')
    person_details = relationship('PersonDetails', back_populates='person')
    person_location = relationship('Location', back_populates='person')
    patient = relationship('Patient', back_populates='patient_person')
    cart = relationship('Cart', back_populates='person')
    service_contribution = relationship('ServiceContribution', back_populates='person')


class PersonDetails(Base):
    __tablename__ = 'person_details'
    __table_args__ = (
        ForeignKeyConstraint(['person_job_ref'], ['staff_role.id_staff_role'], name='fk_person_details_1'),
        Index('fk_person_details_1_idx', 'person_job_ref')
    )

    id_person_details = Column(Integer, primary_key=True)
    person_first_name = Column(String(255))
    person_last_name = Column(String(255))
    person_birth_date = Column(Date)
    person_gender = Column(Enum('Male', 'Female'))
    person_country_code = Column(String(45))
    person_phone = Column(String(45))
    person_languages = Column(String(100))
    person_id_number = Column(String(100))
    person_id_type = Column(Enum('Passport', 'National_ID', 'driving_license'))
    person_id_expiry = Column(Date)
    person_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    person_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    person_job_title = Column(String(255))
    person_job_ref = Column(Integer)
    verified_person_details = Column(TINYINT)
    person_national_number = Column(String(255))
    person_national_ID_reference = Column(String(255))
    person_details_ID_document = Column(Enum('passport', 'ID', 'driving_license'))

    person = relationship('Person', back_populates='person_details')
    staff_role = relationship('StaffRole', back_populates='person_details')


class Plan(Base):
    __tablename__ = 'plan'

    id_plan = Column(Integer, primary_key=True)
    plan_name = Column(String(45))
    plan_price = Column(DECIMAL(10, 2))
    billing_cycle = Column(Enum('monthly', 'semestrial', 'yearly', 'lifetime'), server_default=text("'monthly'"))
    plan_type = Column(Enum('individual', 'organization'), server_default=text("'individual'"))
    plan_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    plan_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    subscription = relationship('Subscription', back_populates='subscription_plan')


class ProvidedServiceCategory(Base):
    __tablename__ = 'provided_service_category'
    __table_args__ = (
        ForeignKeyConstraint(['provided_service_category_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_provided_service_category_1'),
        Index('idx_provided_service_category_active', 'provided_service_category_deleted_at'),
        Index('idx_provided_service_category_created_at', 'provided_service_category_created_at'),
        Index('idx_provided_service_category_name', 'provided_service_category_naming_ref')
    )

    provided_service_category_id = Column(Integer, primary_key=True)
    provided_service_category_name = Column(String(255))
    provided_service_category_naming_ref = Column(Integer)
    provided_service_category_icon_url = Column(String(500))
    provided_service_category_avg_duration = Column(DECIMAL(10, 2), comment='Average duration in minutes')
    provided_service_category_description = Column(Text)
    provided_service_category_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    provided_service_category_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    provided_service_category_deleted_at = Column(TIMESTAMP)

    naming_contribution = relationship('NamingContribution', back_populates='provided_service_category')
    staff_role = relationship('StaffRole', back_populates='provided_service_category')
    provided_service = relationship('ProvidedService', back_populates='provided_service_category')


class SerologyIndicator(Base):
    __tablename__ = 'serology_indicator'

    id_serology_indicator = Column(Integer, primary_key=True)
    serology_indicator_name = Column(String(45))
    serology_indicator_desc = Column(String(300))

    serology = relationship('Serology', back_populates='indicator')


class StaffRole(Base):
    __tablename__ = 'staff_role'
    __table_args__ = (
        ForeignKeyConstraint(['staff_role_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_staff_role_2'),
        ForeignKeyConstraint(['staff_role_service_category_ref'], ['provided_service_category.provided_service_category_id'], name='fk_staff_role_1'),
        Index('fk_staff_role_1_idx', 'staff_role_service_category_ref'),
        Index('fk_staff_role_2_idx', 'staff_role_naming_ref')
    )

    id_staff_role = Column(Integer, primary_key=True)
    staff_role_service_category_ref = Column(Integer)
    staff_role_naming_ref = Column(Integer)
    staff_role_icon_url = Column(String(255))
    staff_role_name = Column(String(255))

    care_giver = relationship('CareGiver', back_populates='staff_role')
    person_details = relationship('PersonDetails', back_populates='staff_role')
    naming_contribution = relationship('NamingContribution', back_populates='staff_role')
    provided_service_category = relationship('ProvidedServiceCategory', back_populates='staff_role')
    service_staff_requirement = relationship('ServiceStaffRequirement', back_populates='staff_role')


class Wallet(Base):
    __tablename__ = 'wallet'

    id_wallet = Column(Integer, primary_key=True)
    wallet_type = Column(Enum('user', 'provider', 'organization', 'system', 'virtual', 'business'), server_default=text("'user'"))
    wallet_currency = Column(Enum('DZD', 'USD', 'EUR'), server_default=text("'DZD'"))
    wallet_balance = Column(DECIMAL(20, 8))
    wallet_status = Column(Enum('active', 'inactive', 'suspended', 'closed', 'pending_verification'), server_default=text("'pending_verification'"))
    wallet_version = Column(Integer, server_default=text("'0'"))

    app_user = relationship('AppUser', back_populates='app_user_wallet')
    delivery_broker = relationship('DeliveryBroker', back_populates='delivery_broker_wallet')
    provider_organisation = relationship('ProviderOrganisation', back_populates='provider_organisation_wallet')
    money_transaction = relationship('MoneyTransaction', foreign_keys='[MoneyTransaction.money_transaction_wallet_destination_id]', back_populates='money_transaction_wallet_destination')
    money_transaction_ = relationship('MoneyTransaction', foreign_keys='[MoneyTransaction.money_transaction_wallet_source_id]', back_populates='money_transaction_wallet_source')
    product_provider = relationship('ProductProvider', back_populates='product_provider_wallet')
    ledger_entry = relationship('LedgerEntry', back_populates='wallet')


class Comment(Base):
    __tablename__ = 'comment'
    __table_args__ = (
        ForeignKeyConstraint(['comment_owner'], ['app_user.id_app_user'], name='fk_comment_2'),
        ForeignKeyConstraint(['replying_to'], ['comment.idcomment'], name='fk_comment_1'),
        Index('fk_comment_1_idx', 'replying_to'),
        Index('fk_comment_2_idx', 'comment_owner')
    )

    idcomment = Column(Integer, primary_key=True)
    comment_owner = Column(Integer)
    comment_content = Column(Text)
    replying_to = Column(Integer)
    comment_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    comment_visibility = Column(TINYINT)
    comment_edition = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    app_user = relationship('AppUser', back_populates='comment')
    comment = relationship('Comment', remote_side=[idcomment], back_populates='comment_reverse')
    comment_reverse = relationship('Comment', remote_side=[replying_to], back_populates='comment')
    comment_reaction = relationship('CommentReaction', back_populates='comment')


class DeliveryBroker(Base):
    __tablename__ = 'delivery_broker'
    __table_args__ = (
        ForeignKeyConstraint(['delivery_broker_wallet_id'], ['wallet.id_wallet'], name='fk_delivery_broker_1'),
        Index('fk_delivery_broker_1_idx', 'delivery_broker_wallet_id')
    )

    id_delivery_broker = Column(Integer, primary_key=True)
    delivery_broker_name = Column(String(255))
    delivery_broker_label = Column(String(255))
    delivery_broker_logo_url = Column(String(255))
    delivery_broker_image_url = Column(String(255))
    delivery_broker_wallet_id = Column(Integer)
    delivery_broker_price_matrix = Column(Text)
    verified_delivery_broker = Column(TINYINT)

    delivery_broker_wallet = relationship('Wallet', back_populates='delivery_broker')
    delivery = relationship('Delivery', back_populates='delivery_broker')


class Discount(Base):
    __tablename__ = 'discount'
    __table_args__ = (
        ForeignKeyConstraint(['discount_user_id'], ['app_user.id_app_user'], name='fk_discount_1'),
        Index('fk_discount_1_idx', 'discount_user_id')
    )

    id_discount = Column(Integer, primary_key=True)
    discount_type = Column(Enum('percentage', 'fixed'), server_default=text("'fixed'"))
    discount_value = Column(DECIMAL(20, 2), server_default=text("'0.00'"))
    discount_code = Column(String(45))
    discount_state = Column(Enum('AVAILABLE', 'USED', 'OBSOLETE'), server_default=text("'AVAILABLE'"))
    discount_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    discount_last_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    discount_user_id = Column(Integer)

    discount_user = relationship('AppUser', back_populates='discount')
    placed_order = relationship('PlacedOrder', back_populates='discount')
    cart = relationship('Cart', back_populates='discount')
    ordered_item = relationship('OrderedItem', back_populates='discount')
    ordered_service = relationship('OrderedService', back_populates='discount')


class Ingredient(Base):
    __tablename__ = 'ingredient'
    __table_args__ = (
        ForeignKeyConstraint(['ingredient_naming_contribution'], ['naming_contribution.id_naming_contribution'], name='fk_ingredient_1'),
        ForeignKeyConstraint(['ingredient_user_id'], ['app_user.id_app_user'], name='fk_ingredient_2'),
        Index('fk_ingredient_1_idx', 'ingredient_naming_contribution'),
        Index('fk_ingredient_2_idx', 'ingredient_user_id')
    )

    id_ingredient = Column(Integer, primary_key=True)
    ingredient_quantifier = Column(Enum('g', 'kg', 'mg', 'L', 'mL', 'pc', 'pkg', 'box', 'bag', 'slice', 'cup'), server_default=text("'pc'"))
    ingredient_naming_contribution = Column(Integer)
    ingredient_icon_url = Column(String(255))
    ingredient_name = Column(String(255))
    ingredient_user_id = Column(Integer)

    naming_contribution = relationship('NamingContribution', back_populates='ingredient')
    ingredient_user = relationship('AppUser', back_populates='ingredient')
    recipe_contains_ingredient = relationship('RecipeContainsIngredient', back_populates='contained_ingredient')



class Notification(Base):
    __tablename__ = 'notification'
    __table_args__ = (
        ForeignKeyConstraint(['notification_user_ref'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_notification_1'),
        Index('fk_notification_1_idx', 'notification_user_ref')
    )

    id_notification = Column(Integer, primary_key=True)
    notification_code = Column(Enum('order_placed', 'order_confirmed', 'order_processing', 'order_shipped', 'order_delivered', 'order_cancelled', 'order_refunded', 'order_status_updated', 'payment_received', 'payment_failed', 'payment_refunded', 'payment_pending', 'invoice_created', 'invoice_paid', 'invoice_overdue', 'invoice_cancelled', 'deposit_received', 'deposit_confirmed', 'cart_abandoned', 'cart_reminder', 'cart_created', 'cart_updated', 'product_added', 'product_updated', 'product_deleted', 'product_stock_low', 'product_stock_restocked', 'product_price_changed', 'product_reviewed', 'product_rating', 'product_featured', 'product_discount', 'product_back_in_stock', 'product_available', 'product_out_of_stock', 'supplier_created', 'supplier_updated', 'supplier_deleted', 'supplier_verified', 'supplier_suspended', 'supplier_approved', 'provider_created', 'provider_updated', 'provider_deleted', 'provider_verified', 'provider_suspended', 'provider_approved', 'role_invitation', 'role_invitation_accepted', 'role_invitation_rejected', 'role_invitation_expired', 'role_assigned', 'role_removed', 'role_updated', 'role_changed', 'permission_granted', 'permission_revoked', 'user_role_changed', 'recipe_added', 'recipe_updated', 'recipe_deleted', 'recipe_liked', 'recipe_commented', 'recipe_featured', 'recipe_shared', 'recipe_saved', 'user_registered', 'user_verified', 'user_password_changed', 'user_profile_updated', 'user_logged_in', 'user_logged_out', 'user_suspended', 'user_reactivated', 'user_deleted', 'user_email_verified', 'user_phone_verified', 'user_account_approved', 'user_account_rejected', 'user_account_pending', 'subscription_created', 'subscription_renewed', 'subscription_expired', 'subscription_cancelled', 'subscription_payment_failed', 'subscription_upgraded', 'subscription_downgraded', 'subscription_trial_ending', 'subscription_payment_success', 'delivery_created', 'delivery_confirmed', 'delivery_shipped', 'delivery_in_transit', 'delivery_out_for_delivery', 'delivery_delivered', 'delivery_failed', 'delivery_cancelled', 'delivery_returned', 'delivery_refunded', 'delivery_status_updated', 'delivery_scheduled', 'delivery_delayed', 'service_created', 'service_updated', 'service_deleted', 'service_scheduled', 'service_completed', 'service_cancelled', 'service_reminder', 'service_rescheduled', 'service_reviewed', 'service_rating', 'service_confirmed', 'service_started', 'service_finished', 'comment_added', 'comment_replied', 'comment_mentioned', 'comment_liked', 'comment_deleted', 'comment_reported', 'comment_approved', 'comment_spam', 'reaction_received', 'reaction_liked', 'reaction_loved', 'reaction_rated', 'reaction_disliked', 'report_created', 'report_processed', 'report_resolved', 'report_closed', 'report_rejected', 'report_escalated', 'wallet_credited', 'wallet_debited', 'wallet_balance_low', 'wallet_balance_updated', 'wallet_created', 'wallet_activated', 'wallet_suspended', 'wallet_closed', 'wallet_pending_verification', 'wallet_verified', 'wallet_transaction_completed', 'money_transaction_initiated', 'money_transaction_completed', 'money_transaction_failed', 'money_transaction_reversed', 'money_transaction_cancelled', 'money_transaction_refunded', 'money_transaction_pending', 'org_invitation', 'org_invitation_accepted', 'org_invitation_rejected', 'org_member_added', 'org_member_removed', 'org_member_left', 'org_created', 'org_updated', 'org_deleted', 'org_activated', 'org_suspended', 'team_invitation', 'team_invitation_accepted', 'team_invitation_rejected', 'team_member_added', 'team_member_removed', 'team_created', 'team_updated', 'team_deleted', 'welcome', 'onboarding_complete', 'profile_updated', 'account_created', 'account_suspended', 'account_reactivated', 'account_deleted', 'settings_updated', 'preferences_updated', 'security_alert', 'security_alert_unusual_login', 'security_alert_password_change', 'security_alert_two_factor', 'security_alert_device_recognized', 'security_alert_device_unknown', 'system_announcement', 'maintenance_scheduled', 'maintenance_completed', 'new_version_available', 'feature_available', 'newsletter', 'promotional_offer', 'discount_available', 'coupon_received', 'loyalty_points_earned', 'loyalty_points_used', 'birthday_greeting', 'milestone_achieved', 'feedback_request', 'survey_request', 'upcoming_event', 'event_reminder', 'event_cancelled', 'event_postponed', 'notification_preference_updated', 'notification_settings_changed', 'unread_messages', 'new_message_received', 'message_read', 'message_sent', 'message_failed', 'conversation_started', 'conversation_ended', 'conversation_updated', 'connection_request', 'connection_approved', 'connection_rejected', 'connection_removed', 'connection_suggested', 'follow_request', 'follow_request_accepted', 'follow_request_rejected', 'follow_started', 'follow_ended', 'share_received', 'share_accepted', 'share_rejected', 'share_expired', 'review_requested', 'review_submitted', 'review_updated', 'review_deleted', 'review_responded', 'appointment_scheduled', 'appointment_confirmed', 'appointment_rescheduled', 'appointment_cancelled', 'appointment_reminder', 'appointment_completed', 'appointment_no_show', 'task_assigned', 'task_updated', 'task_completed', 'task_overdue', 'task_deleted', 'task_reassigned', 'document_uploaded', 'document_shared', 'document_updated', 'document_deleted', 'document_expired', 'document_approved', 'document_rejected', 'document_signed', 'compliance_alert', 'compliance_approved', 'compliance_rejected', 'compliance_updated', 'compliance_reminder', 'compliance_due', 'compliance_overdue', 'backup_completed', 'backup_failed', 'backup_restored', 'backup_scheduled', 'integration_connected', 'integration_disconnected', 'integration_error', 'integration_success', 'integration_sync_completed', 'integration_sync_failed'))
    notification_params = Column(Text)
    notification_user_ref = Column(Integer)
    notification_created_at = Column(DateTime)
    notification_read_at = Column(DateTime)

    app_user = relationship('AppUser', back_populates='notification')
    role_invitation = relationship('RoleInvitation', back_populates='notification')


class Patient(Base):
    __tablename__ = 'patient'
    __table_args__ = (
        ForeignKeyConstraint(['patient_person_id'], ['person.id_person'], name='fk_patient_1'),
        Index('fk_patient_1_idx', 'patient_person_id')
    )

    id_patient = Column(Integer, primary_key=True)
    patient_person_id = Column(Integer)
    patient_disease_severity = Column(Enum('mild', 'moderate', 'severe', 'critical'), server_default=text("'mild'"))

    patient_person = relationship('Person', back_populates='patient')
    diagnosis = relationship('Diagnosis', back_populates='patient')
    serology = relationship('Serology', back_populates='patient')
    symptoms_occurence = relationship('SymptomsOccurence', back_populates='patient')


class Payment(Base):
    __tablename__ = 'payment'
    __table_args__ = (
        ForeignKeyConstraint(['payment_invoice_id'], ['invoice.invoice_id'], ondelete='RESTRICT', onupdate='CASCADE', name='payment_ibfk_1'),
        Index('idx_invoice', 'payment_invoice_id'),
        Index('idx_status', 'payment_status')
    )

    payment_id = Column(Integer, primary_key=True)
    payment_invoice_id = Column(Integer)
    payment_amount = Column(DECIMAL(15, 4))
    payment_method = Column(Enum('cash', 'card', 'bank_transfer', 'mobile_money', 'crypto', 'deposit', 'wallet', 'check'), server_default=text("'cash'"), comment='cash, card, bank, mobile')
    payment_status = Column(Enum('pending', 'processing', 'completed', 'partial', 'failed', 'cancelled'), server_default=text("'pending'"))
    payment_reference = Column(String(255), comment='Bank or transaction reference')
    payment_notes = Column(Text)
    payment_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    payment_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    payment_type = Column(Enum('deposit', 'payment', 'refund'))

    payment_invoice = relationship('Invoice', back_populates='payment')
    money_transaction = relationship('MoneyTransaction', back_populates='payment')
    subscription = relationship('Subscription', back_populates='subscription_payment')


class ProductCategory(Base):
    __tablename__ = 'product_category'
    __table_args__ = (
        ForeignKeyConstraint(['product_category_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_product_category_1'),
        Index('fk_product_category_1_idx', 'product_category_naming_ref')
    )

    id_product_category = Column(Integer, primary_key=True)
    product_category_naming_ref = Column(Integer)
    product_category_icon = Column(String(255))
    product_category_name = Column(String(255))

    naming_contribution = relationship('NamingContribution', back_populates='product_category')
    iproduct = relationship('Iproduct', back_populates='iproduct_category')
    product = relationship('Product', back_populates='product_category')


class ProductProviderType(Base):
    __tablename__ = 'product_provider_type'
    __table_args__ = (
        ForeignKeyConstraint(['product_provider_type_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_product_provider_type_1'),
        Index('fk_product_provider_type_1_idx', 'product_provider_type_naming_ref')
    )

    id_product_provider_type = Column(Integer, primary_key=True)
    product_provider_type_naming_ref = Column(Integer)
    product_provider_type_icon_url = Column(String(255))
    product_provider_type_name = Column(String(255))

    naming_contribution = relationship('NamingContribution', back_populates='product_provider_type')
    product_provider = relationship('ProductProvider', back_populates='product_provider_type')


class ProviderDetails(Base):
    __tablename__ = 'provider_details'
    __table_args__ = (
        ForeignKeyConstraint(['provider_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_provider_details_1'),
        Index('fk_provider_details_1_idx', 'provider_naming_ref')
    )

    idprovider_details_id = Column(Integer, primary_key=True)
    provider_naming_ref = Column(Integer)
    provider_contact_info = Column(Text)
    provider_name = Column(String(255))
    provider_details_icon_url = Column(String(255))

    naming_contribution = relationship('NamingContribution', back_populates='provider_details')
    product_provider = relationship('ProductProvider', back_populates='product_provider_details')


class ProviderOrganisation(Base):
    __tablename__ = 'provider_organisation'
    __table_args__ = (
        ForeignKeyConstraint(['app_user_id'], ['app_user.id_app_user'], name='fk_provider_organisation_app_user1'),
        ForeignKeyConstraint(['provider_organisation_naming'], ['naming_contribution.id_naming_contribution'], name='fk_provider_organisation_2'),
        ForeignKeyConstraint(['provider_organisation_wallet_id'], ['wallet.id_wallet'], name='fk_provider_organisation_1'),
        Index('fk_provider_organisation_1_idx', 'provider_organisation_wallet_id'),
        Index('fk_provider_organisation_2_idx', 'provider_organisation_naming'),
        Index('fk_provider_organisation_app_user1_idx', 'app_user_id')
    )

    idprovider_organisation = Column(Integer, primary_key=True)
    provider_organisation_naming = Column(Integer)
    provider_organisation_wallet_id = Column(Integer)
    provider_organisation_name = Column(String(255))
    provider_organisation_icon_url = Column(String(255))
    provider_organisation_desc = Column(String(255))
    app_user_id = Column(Integer)
    verified_organisation = Column(TINYINT)

    app_user = relationship('AppUser', back_populates='provider_organisation')
    naming_contribution = relationship('NamingContribution', back_populates='provider_organisation')
    provider_organisation_wallet = relationship('Wallet', back_populates='provider_organisation')
    organisation_image = relationship('OrganisationImage', back_populates='org_ref')
    product_provider = relationship('ProductProvider', back_populates='product_provider_org')
    conversation = relationship('Conversation', back_populates='conversation_org')
    management_rule = relationship('ManagementRule', back_populates='provider_organisation')
    role_invitation = relationship('RoleInvitation', back_populates='organisation')
    service_contribution = relationship('ServiceContribution', back_populates='provider_organisation')


class RecipeCategory(Base):
    __tablename__ = 'recipe_category'
    __table_args__ = (
        ForeignKeyConstraint(['recipe_category_naming'], ['naming_contribution.id_naming_contribution'], name='fk_recipe_category_1'),
        Index('fk_recipe_category_1_idx', 'recipe_category_naming')
    )

    id_recipe_category = Column(Integer, primary_key=True)
    recipe_category_naming = Column(Integer)
    recipe_category_icon_url = Column(String(255))
    recipe_category_name = Column(String(255))

    naming_contribution = relationship('NamingContribution', back_populates='recipe_category')
    recipe = relationship('Recipe', back_populates='recipe_category')


class Report(Base):
    __tablename__ = 'report'
    __table_args__ = (
        ForeignKeyConstraint(['report_owner'], ['app_user.id_app_user'], name='fk_report_1'),
        Index('fk_report_1_idx', 'report_owner')
    )

    id_report = Column(Integer, primary_key=True)
    report_text = Column(Text)
    report_owner = Column(Integer)
    report_type = Column(Enum('spam', 'abuse', 'harassment', 'offensive_content', 'inappropriate_content', 'hate_speech', 'bullying', 'threatening', 'violent_content', 'adult_content', 'misinformation', 'fake_news', 'scam', 'fraud', 'phishing', 'malware', 'virus', 'security_issue', 'privacy_issue', 'data_breach', 'product_misrepresentation', 'counterfeit_product', 'product_safety_concern', 'expired_product', 'damaged_product', 'wrong_product', 'product_quality_issue', 'product_quantity_issue', 'product_price_issue', 'product_availability_issue', 'provider_fraud', 'provider_scam', 'provider_poor_service', 'provider_unresponsive', 'provider_misleading', 'provider_fake_reviews', 'provider_duplicate', 'provider_suspended_activity', 'provider_unauthorized_charges', 'fake_account', 'impersonation', 'identity_theft', 'user_harassment', 'user_abuse', 'user_spam', 'user_misconduct', 'user_violation', 'user_underage', 'user_inappropriate_behavior', 'recipe_inaccurate', 'recipe_unsafe', 'recipe_allergen_issue', 'recipe_misleading', 'recipe_copycat', 'recipe_fake', 'recipe_offensive', 'recipe_dangerous_ingredients', 'recipe_incorrect_instructions', 'service_misrepresentation', 'service_unprofessional', 'service_cancelled_no_show', 'service_quality_issue', 'service_safety_concern', 'service_incomplete', 'service_overcharged', 'service_unavailable', 'service_fake', 'delivery_misrepresentation', 'delivery_unprofessional', 'delivery_cancelled_no_show', 'delivery_quality_issue', 'delivery_safety_concern', 'delivery_incomplete', 'delivery_overcharged', 'delivery_unavailable', 'delivery_fake', 'order_fraud', 'order_scam', 'order_dispute', 'order_missing_items', 'order_wrong_items', 'order_delivery_issue', 'order_payment_issue', 'order_refund_issue', 'order_cancellation_issue', 'payment_fraud', 'payment_unauthorized', 'payment_overcharged', 'payment_double_charged', 'payment_refund_issue', 'payment_missing', 'financial_fraud', 'financial_misrepresentation', 'financial_unauthorized_charges', 'financial_discrepancy', 'financial_missing_transaction', 'financial_duplicate_transaction', 'review_fake', 'review_bought', 'review_offensive', 'review_spam', 'review_irrelevant', 'review_duplicate', 'review_misleading', 'review_inappropriate', 'comment_spam', 'comment_abuse', 'comment_harassment', 'comment_offensive', 'comment_inappropriate', 'comment_hate_speech', 'comment_fake', 'payment_dispute', 'payment_reversal', 'payment_chargeback', 'payment_refund_request', 'payment_unauthorized_charge', 'payment_billing_error', 'system_bug', 'system_error', 'system_performance_issue', 'system_security_issue', 'system_data_issue', 'system_integration_issue', 'system_ui_issue', 'system_feature_request', 'system_enhancement', 'copyright_infringement', 'trademark_infringement', 'intellectual_property_violation', 'defamation', 'libel', 'slander', 'confidential_info_leak', 'trade_secret_violation', 'terms_violation', 'policy_violation', 'community_guidelines_violation', 'legal_issue', 'support_request', 'support_issue', 'support_complaint', 'support_feedback', 'support_suggestion', 'support_compliment', 'support_bug_report', 'support_feature_request', 'other', 'general_complaint', 'general_feedback', 'general_inquiry', 'general_issue'), server_default=text("'other'"))
    report_appreciation = Column(Enum('valid', 'plausible', 'invalid'))
    report_appreciation_value = Column(Float)

    app_user = relationship('AppUser', back_populates='report')


class Symptom(Base):
    __tablename__ = 'symptom'
    __table_args__ = (
        ForeignKeyConstraint(['symptom_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_symptom_1'),
        Index('fk_symptom_1_idx', 'symptom_naming_ref')
    )

    id_symptom = Column(Integer, primary_key=True)
    symptom_naming_ref = Column(Integer)
    symptom_icon_url = Column(String(255))

    naming_contribution = relationship('NamingContribution', back_populates='symptom')
    presented_symptom = relationship('PresentedSymptom', back_populates='symptom')


class CommentReaction(Base):
    __tablename__ = 'comment_reaction'
    __table_args__ = (
        ForeignKeyConstraint(['comment_reacting_user'], ['app_user.id_app_user'], onupdate='RESTRICT', name='fk_product_reaction_11'),
        ForeignKeyConstraint(['reacted_on_comment'], ['comment.idcomment'], name='fk_product_reaction_30'),
        Index('fk_product_reaction_1_idx', 'comment_reacting_user'),
        Index('fk_product_reaction_30_idx', 'reacted_on_comment')
    )

    id_comment_reaction = Column(Integer, primary_key=True)
    comment_reacting_user = Column(Integer)
    comment_reaction = Column(Enum('like', 'dislike', 'love', 'helpful', 'not_helpful', 'star'), server_default=text("'like'"))
    reacted_on_comment = Column(Integer)

    app_user = relationship('AppUser', back_populates='comment_reaction')
    comment = relationship('Comment', back_populates='comment_reaction')


class Diagnosis(Base):
    __tablename__ = 'diagnosis'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['care_giver.id_care_giver'], name='fk_diagnosis_doctor1'),
        ForeignKeyConstraint(['patient_id'], ['patient.id_patient'], name='fk_diagnosis_patient1'),
        Index('fk_diagnosis_doctor1_idx', 'doctor_id'),
        Index('fk_diagnosis_patient1_idx', 'patient_id')
    )

    id_diagnosis = Column(Integer, primary_key=True)
    patient_id = Column(Integer)
    doctor_id = Column(Integer)
    diagnosis_date = Column(Date)

    doctor = relationship('CareGiver', back_populates='diagnosis')
    patient = relationship('Patient', back_populates='diagnosis')
    prescription = relationship('Prescription', back_populates='diagnosis')


class Iproduct(Base):
    __tablename__ = 'iproduct'
    __table_args__ = (
        ForeignKeyConstraint(['iproduct_category_id'], ['product_category.id_product_category'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_iproduct_1'),
        ForeignKeyConstraint(['iproduct_naming_ref'], ['naming_contribution.id_naming_contribution'], name='fk_iproduct_2'),
        Index('fk_iproduct_1_idx', 'iproduct_category_id'),
        Index('fk_iproduct_2_idx', 'iproduct_naming_ref')
    )

    id_iproduct = Column(Integer, primary_key=True)
    iproduct_barcode = Column(String(45))
    iproduct_brand = Column(String(255))
    iproduct_estimated_price = Column(DECIMAL(8, 2), server_default=text("'0.00'"))
    iproduct_price_currency = Column(String(45), server_default=text("'DZD'"))
    iproduct_gluten_status = Column(Enum('gluten_free', 'contains_gluten', 'may_contain_gluten', 'unknown'), server_default=text("'unknown'"))
    iproduct_info_source = Column(String(255))
    iproduct_last_price_update = Column(DateTime)
    iproduct_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    iproduct_last_update = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    iproduct_model_name = Column(String(255))
    iproduct_image_url = Column(String(255))
    iproduct_naming_ref = Column(Integer)
    iproduct_info_confidence = Column(DECIMAL(5, 4))
    iproduct_category_id = Column(Integer)
    iproduct_name = Column(String(255))

    iproduct_category = relationship('ProductCategory', back_populates='iproduct')
    naming_contribution = relationship('NamingContribution', back_populates='iproduct')
    product = relationship('Product', back_populates='product_origin')
    prescribed_item = relationship('PrescribedItem', back_populates='iproduct')


class LocationImage(Base):
    __tablename__ = 'location_image'
    __table_args__ = (
        ForeignKeyConstraint(['image_location_ref'], ['location.id_location'], name='fk_location_image_1'),
        Index('fk_location_image_1_idx', 'image_location_ref')
    )

    id_location_image = Column(Integer, primary_key=True)
    location_image_url = Column(String(255))
    image_location_ref = Column(Integer)

    location = relationship('Location', back_populates='location_image')


class MoneyTransaction(Base):
    __tablename__ = 'money_transaction'
    __table_args__ = (
        ForeignKeyConstraint(['money_transaction_for_payment'], ['payment.payment_id'], name='fk_money_transaction_3'),
        ForeignKeyConstraint(['money_transaction_wallet_destination_id'], ['wallet.id_wallet'], name='fk_money_transaction_2'),
        ForeignKeyConstraint(['money_transaction_wallet_source_id'], ['wallet.id_wallet'], name='fk_money_transaction_1'),
        Index('fk_money_transaction_1_idx', 'money_transaction_wallet_source_id'),
        Index('fk_money_transaction_2_idx', 'money_transaction_wallet_destination_id'),
        Index('fk_money_transaction_3_idx', 'money_transaction_for_payment')
    )

    id_money_transaction = Column(Integer, primary_key=True)
    money_transaction_document_url = Column(String(255))
    money_transaction_amount = Column(DECIMAL(20, 8), server_default=text("'0.00000000'"))
    money_transaction_reference = Column(String(255))
    money_transaction_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    money_transaction_last_updated = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    money_transaction_wallet_source_id = Column(Integer)
    money_transaction_wallet_destination_id = Column(Integer)
    money_transaction_status = Column(Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'reversed'), server_default=text("'pending'"))
    money_transaction_for_payment = Column(Integer)

    payment = relationship('Payment', back_populates='money_transaction')
    money_transaction_wallet_destination = relationship('Wallet', foreign_keys=[money_transaction_wallet_destination_id], back_populates='money_transaction')
    money_transaction_wallet_source = relationship('Wallet', foreign_keys=[money_transaction_wallet_source_id], back_populates='money_transaction_')
    ledger_entry = relationship('LedgerEntry', back_populates='money_transaction')


class OrganisationImage(Base):
    __tablename__ = 'organisation_image'
    __table_args__ = (
        ForeignKeyConstraint(['org_ref_id'], ['provider_organisation.idprovider_organisation'], name='fk_organisation_image_1'),
        Index('fk_organisation_image_1_idx', 'org_ref_id')
    )

    id_org_image = Column(Integer, primary_key=True)
    org_image_url = Column(String(255))
    org_ref_id = Column(Integer)

    org_ref = relationship('ProviderOrganisation', back_populates='organisation_image')


class PlacedOrder(Base):
    __tablename__ = 'placed_order'
    __table_args__ = (
        ForeignKeyConstraint(['discount_id'], ['discount.id_discount'], name='fk_placed_order_4'),
        ForeignKeyConstraint(['ordering_user_id'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_placed_order_1'),
        ForeignKeyConstraint(['placed_order_invoice'], ['invoice.invoice_id'], name='fk_placed_order_3'),
        ForeignKeyConstraint(['placed_order_location_ref'], ['location.id_location'], name='fk_placed_order_2'),
        Index('fk_placed_order_1_idx', 'ordering_user_id'),
        Index('fk_placed_order_2_idx', 'placed_order_location_ref'),
        Index('fk_placed_order_3_idx', 'placed_order_invoice'),
        Index('fk_placed_order_4_idx', 'discount_id')
    )

    id_placed_order = Column(Integer, primary_key=True)
    order_discount = Column(Float(asdecimal=True))
    total_price = Column(Float(asdecimal=True))
    ordering_user_id = Column(Integer)
    placed_order_location_ref = Column(Integer)
    placed_order_state = Column(Enum('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED'), server_default=text("'PENDING'"))
    placed_order_last_mod = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    placed_order_receipt_ref = Column(Integer)
    placed_order_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    placed_order_invoice = Column(Integer)
    discount_id = Column(Integer)

    discount = relationship('Discount', back_populates='placed_order')
    ordering_user = relationship('AppUser', back_populates='placed_order')
    invoice = relationship('Invoice', back_populates='placed_order')
    location = relationship('Location', back_populates='placed_order')
    ordered_item = relationship('OrderedItem', back_populates='placed_order')


class ProductProvider(Base):
    __tablename__ = 'product_provider'
    __table_args__ = (
        ForeignKeyConstraint(['product_provider_details_id'], ['provider_details.idprovider_details_id'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_3'),
        ForeignKeyConstraint(['product_provider_location_id'], ['location.id_location'], name='fk_product_provider_4'),
        ForeignKeyConstraint(['product_provider_org_id'], ['provider_organisation.idprovider_organisation'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_2'),
        ForeignKeyConstraint(['product_provider_owner'], ['app_user.id_app_user'], name='fk_product_provider_5'),
        ForeignKeyConstraint(['product_provider_type_id'], ['product_provider_type.id_product_provider_type'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_1'),
        ForeignKeyConstraint(['product_provider_wallet_id'], ['wallet.id_wallet'], name='fk_product_provider_6'),
        Index('fk_product_provider_1_idx', 'product_provider_type_id'),
        Index('fk_product_provider_2_idx', 'product_provider_org_id'),
        Index('fk_product_provider_3_idx', 'product_provider_details_id'),
        Index('fk_product_provider_4_idx', 'product_provider_location_id'),
        Index('fk_product_provider_5_idx', 'product_provider_owner'),
        Index('fk_product_provider_6_idx', 'product_provider_wallet_id')
    )

    id_product_provider = Column(Integer, primary_key=True)
    product_provider_details_id = Column(Integer)
    product_provider_type_id = Column(Integer)
    product_provider_location_id = Column(Integer)
    product_provider_org_id = Column(Integer)
    product_provider_owner = Column(Integer)
    product_provider_wallet_id = Column(Integer)
    verified_provider = Column(TINYINT)

    product_provider_details = relationship('ProviderDetails', back_populates='product_provider')
    product_provider_location = relationship('Location', back_populates='product_provider')
    product_provider_org = relationship('ProviderOrganisation', back_populates='product_provider')
    app_user = relationship('AppUser', back_populates='product_provider')
    product_provider_type = relationship('ProductProviderType', back_populates='product_provider')
    product_provider_wallet = relationship('Wallet', back_populates='product_provider')
    additional_fee = relationship('AdditionalFee', back_populates='additional_fee_on_provider')
    cart = relationship('Cart', back_populates='cart_product_provider')
    conversation = relationship('Conversation', back_populates='conversation_provider')
    delivery = relationship('Delivery', back_populates='delivery_provider')
    management_rule = relationship('ManagementRule', back_populates='product_provider')
    product = relationship('Product', back_populates='product_provider')
    provided_service = relationship('ProvidedService', back_populates='provided_service_product_provider')
    provider_image = relationship('ProviderImage', back_populates='provider_ref')
    provider_reaction = relationship('ProviderReaction', back_populates='product_provider')
    service_package = relationship('ServicePackage', back_populates='service_package_product_provider')
    role_invitation = relationship('RoleInvitation', back_populates='provider')
    service_contribution = relationship('ServiceContribution', back_populates='product_provider')


class Recipe(Base):
    __tablename__ = 'recipe'
    __table_args__ = (
        ForeignKeyConstraint(['recipe_category_id'], ['recipe_category.id_recipe_category'], name='fk_recipe_2'),
        ForeignKeyConstraint(['recipe_owner_id'], ['app_user.id_app_user'], name='fk_recipe_1'),
        Index('fk_recipe_1_idx', 'recipe_owner_id'),
        Index('fk_recipe_2_idx', 'recipe_category_id')
    )

    id_recipe = Column(Integer, primary_key=True)
    recipe_owner_id = Column(Integer)
    recipe_category_id = Column(Integer)
    recipe_preparation_time = Column(String(45))
    recipe_instructions = Column(Text)
    recipe_name = Column(String(255))
    recipe_description = Column(String(300))
    recipe_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    recipe_last_updated = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    recipe_category = relationship('RecipeCategory', back_populates='recipe')
    recipe_owner = relationship('AppUser', back_populates='recipe')
    recipe_contains_ingredient = relationship('RecipeContainsIngredient', back_populates='containing_recipe')
    recipe_image = relationship('RecipeImage', back_populates='recipe_ref')
    recipe_reaction = relationship('RecipeReaction', back_populates='recipe')


class Serology(Base):
    __tablename__ = 'serology'
    __table_args__ = (
        ForeignKeyConstraint(['indicator_id'], ['serology_indicator.id_serology_indicator'], name='fk_serology_1'),
        ForeignKeyConstraint(['patient_id'], ['patient.id_patient'], name='fk_diagnosis_1'),
        Index('fk_diagnosis_1_idx', 'patient_id'),
        Index('fk_serology_1_idx', 'indicator_id')
    )

    id_serology = Column(Integer, primary_key=True)
    indicator_id = Column(Integer)
    serology_date = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    patient_id = Column(Integer)
    indicator_value = Column(String(45))

    indicator = relationship('SerologyIndicator', back_populates='serology')
    patient = relationship('Patient', back_populates='serology')


class Subscription(Base):
    __tablename__ = 'subscription'
    __table_args__ = (
        ForeignKeyConstraint(['subscription_payment_id'], ['payment.payment_id'], name='fk_subscription_2'),
        ForeignKeyConstraint(['subscription_plan_id'], ['plan.id_plan'], name='fk_subscription_1'),
        Index('fk_subscription_1_idx', 'subscription_plan_id'),
        Index('fk_subscription_2_idx', 'subscription_payment_id')
    )

    id_subscription = Column(Integer, primary_key=True)
    subscription_plan_id = Column(Integer)
    subscription_payment_id = Column(Integer)
    subscription_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    subscription_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    subscription_expiry = Column(TIMESTAMP)
    subscription_quota = Column(Integer, server_default=text("'0'"))

    app_user = relationship('AppUser', back_populates='subscription')
    subscription_payment = relationship('Payment', back_populates='subscription')
    subscription_plan = relationship('Plan', back_populates='subscription')


class SymptomsOccurence(Base):
    __tablename__ = 'symptoms_occurence'
    __table_args__ = (
        ForeignKeyConstraint(['symptoms_occurence_ref_patient'], ['patient.id_patient'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_symptoms_causality_1'),
        Index('fk_symptoms_causality_1_idx', 'symptoms_occurence_ref_patient')
    )

    id_symptoms_occurence = Column(Integer, primary_key=True)
    symptoms_occurence_submission_time = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    symptoms_occurence_reason = Column(String(300))
    reason_date = Column(TIMESTAMP)
    symptoms_occurence_ref_patient = Column(Integer)

    patient = relationship('Patient', back_populates='symptoms_occurence')
    presented_symptom = relationship('PresentedSymptom', back_populates='symptoms_occurence')


class AdditionalFee(Base):
    __tablename__ = 'additional_fee'
    __table_args__ = (
        ForeignKeyConstraint(['additional_fee_invoice'], ['invoice.invoice_id'], name='fk_additional_fee_3'),
        ForeignKeyConstraint(['additional_fee_on_provider_id'], ['product_provider.id_product_provider'], name='fk_additional_fee_2'),
        ForeignKeyConstraint(['additional_fee_user_id'], ['app_user.id_app_user'], name='fk_additional_fee_1'),
        Index('fk_additional_fee_1_idx', 'additional_fee_user_id'),
        Index('fk_additional_fee_2_idx', 'additional_fee_on_provider_id'),
        Index('fk_additional_fee_3_idx', 'additional_fee_invoice')
    )

    additional_fee_id = Column(Integer, primary_key=True)
    additional_fee_name = Column(String(255))
    additional_fee_amount = Column(DECIMAL(15, 4))
    additional_fee_description = Column(Text)
    additional_fee_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    additional_fee_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    additional_fee_document_url = Column(String(255))
    additional_fee_user_id = Column(Integer)
    additional_fee_on_provider_id = Column(Integer)
    additional_fee_invoice = Column(Integer)

    invoice = relationship('Invoice', back_populates='additional_fee')
    additional_fee_on_provider = relationship('ProductProvider', back_populates='additional_fee')
    additional_fee_user = relationship('AppUser', back_populates='additional_fee')


class Cart(Base):
    __tablename__ = 'cart'
    __table_args__ = (
        ForeignKeyConstraint(['cart_client_user'], ['app_user.id_app_user'], name='fk_cart_2'),
        ForeignKeyConstraint(['cart_invoice'], ['invoice.invoice_id'], name='fk_cart_5'),
        ForeignKeyConstraint(['cart_person_ref'], ['person.id_person'], name='fk_cart_3'),
        ForeignKeyConstraint(['cart_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='cart_ibfk_1'),
        ForeignKeyConstraint(['cart_selling_user'], ['app_user.id_app_user'], name='fk_cart_1'),
        ForeignKeyConstraint(['discount_id'], ['discount.id_discount'], name='fk_cart_4'),
        Index('fk_cart_2', 'cart_client_user'),
        Index('fk_cart_3_idx', 'cart_person_ref'),
        Index('fk_cart_4_idx', 'discount_id'),
        Index('fk_cart_5_idx', 'cart_invoice'),
        Index('idx_cart_provider', 'cart_product_provider_id'),
        Index('idx_cart_status', 'cart_status'),
        Index('idx_cart_user', 'cart_selling_user')
    )

    cart_id = Column(Integer, primary_key=True)
    cart_product_provider_id = Column(Integer, comment='Provider owning the cart')
    cart_selling_user = Column(Integer, comment='Customer / patient / client id')
    cart_status = Column(Enum('open', 'pending', 'completed', 'canceled', 'partial', 'checkout', 'abandoned'), server_default=text("'open'"), comment='open, pending, completed, canceled')
    cart_total_amount = Column(DECIMAL(15, 4), server_default=text("'0.0000'"))
    cart_notes = Column(Text)
    cart_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    cart_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    cart_person_ref = Column(Integer)
    cart_client_user = Column(Integer)
    cart_due_date = Column(Date)
    cart_invoice = Column(Integer)
    discount_id = Column(Integer)

    app_user = relationship('AppUser', foreign_keys=[cart_client_user], back_populates='cart')
    invoice = relationship('Invoice', back_populates='cart')
    person = relationship('Person', back_populates='cart')
    cart_product_provider = relationship('ProductProvider', back_populates='cart')
    app_user_ = relationship('AppUser', foreign_keys=[cart_selling_user], back_populates='cart_')
    discount = relationship('Discount', back_populates='cart')
    ordered_item = relationship('OrderedItem', back_populates='cart')
    ordered_service = relationship('OrderedService', back_populates='ordered_service_cart')


class Conversation(Base):
    __tablename__ = 'conversation'
    __table_args__ = (
        ForeignKeyConstraint(['conversation_destination_user_id'], ['app_user.id_app_user'], name='fk_message_2'),
        ForeignKeyConstraint(['conversation_org_id'], ['provider_organisation.idprovider_organisation'], name='fk_message_4'),
        ForeignKeyConstraint(['conversation_provider_id'], ['product_provider.id_product_provider'], name='fk_message_3'),
        ForeignKeyConstraint(['conversation_sender_user_id'], ['app_user.id_app_user'], name='fk_message_1'),
        Index('fk_message_1_idx', 'conversation_sender_user_id'),
        Index('fk_message_2_idx', 'conversation_destination_user_id'),
        Index('fk_message_3_idx', 'conversation_provider_id'),
        Index('fk_message_4_idx', 'conversation_org_id')
    )

    id_conversation = Column(Integer, primary_key=True)
    conversation_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    conversation_org_id = Column(Integer)
    conversation_provider_id = Column(Integer)
    conversation_sender_user_id = Column(Integer)
    conversation_destination_user_id = Column(Integer)
    conversation_type = Column(Enum('direct', 'group', 'organization', 'provider'), server_default=text("'direct'"))

    conversation_destination_user = relationship('AppUser', foreign_keys=[conversation_destination_user_id], back_populates='conversation')
    conversation_org = relationship('ProviderOrganisation', back_populates='conversation')
    conversation_provider = relationship('ProductProvider', back_populates='conversation')
    conversation_sender_user = relationship('AppUser', foreign_keys=[conversation_sender_user_id], back_populates='conversation_')
    message = relationship('Message', back_populates='message_conversation')


class Delivery(Base):
    __tablename__ = 'delivery'
    __table_args__ = (
        ForeignKeyConstraint(['delivery_address_id'], ['address.id_address'], name='fk_delivery_1'),
        ForeignKeyConstraint(['delivery_broker_id'], ['delivery_broker.id_delivery_broker'], name='fk_delivery_5'),
        ForeignKeyConstraint(['delivery_current_address_id'], ['address.id_address'], name='fk_delivery_2'),
        ForeignKeyConstraint(['delivery_invoice_ref'], ['invoice.invoice_id'], name='fk_delivery_7'),
        ForeignKeyConstraint(['delivery_provider_id'], ['product_provider.id_product_provider'], name='fk_delivery_4'),
        Index('fk_delivery_1_idx', 'delivery_address_id'),
        Index('fk_delivery_2_idx', 'delivery_current_address_id'),
        Index('fk_delivery_4_idx', 'delivery_provider_id'),
        Index('fk_delivery_5_idx', 'delivery_broker_id'),
        Index('fk_delivery_7_idx', 'delivery_invoice_ref')
    )

    id_delivery = Column(Integer, primary_key=True)
    recipient_person = Column(Integer)
    recipient_provider = Column(Integer)
    delivery_package_count = Column(Integer)
    delivery_total_weight = Column(DECIMAL(10, 0))
    delivery_cargo_dimensions = Column(String(255))
    delivery_goods_description = Column(Text)
    hs_code = Column(String(255))
    delivery_merchant_name = Column(String(255))
    delivery_shipping_method = Column(Enum('standard', 'express', 'overnight', 'pickup', 'courier', 'same_day', 'international'), server_default=text("'standard'"))
    delivery_special_instructions = Column(String(45))
    delivery_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    delivery_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    delivery_status = Column(Enum('pending', 'processing', 'confirmed', 'shipped', 'in_transit', 'out_for_delivery', 'delivered', 'failed', 'cancelled', 'returned', 'refunded'), server_default=text("'pending'"))
    delivery_address_id = Column(Integer)
    delivery_current_address_id = Column(Integer)
    delivery_fee = Column(Float(asdecimal=True), server_default=text("'0'"))
    delivery_provider_id = Column(Integer)
    delivery_broker_id = Column(Integer)
    delivery_invoice_ref = Column(Integer)
    delivery_source_type = Column(Enum('cart', 'placed_order'))
    delivery_source_id = Column(Integer)

    delivery_address = relationship('Address', foreign_keys=[delivery_address_id], back_populates='delivery')
    delivery_broker = relationship('DeliveryBroker', back_populates='delivery')
    delivery_current_address = relationship('Address', foreign_keys=[delivery_current_address_id], back_populates='delivery_')
    invoice = relationship('Invoice', back_populates='delivery')
    delivery_provider = relationship('ProductProvider', back_populates='delivery')


class LedgerEntry(Base):
    __tablename__ = 'ledger_entry'
    __table_args__ = (
        ForeignKeyConstraint(['money_transaction_id'], ['money_transaction.id_money_transaction'], name='fk_ledger_entry_money_transaction1'),
        ForeignKeyConstraint(['wallet_id'], ['wallet.id_wallet'], name='fk_ledger_entry_wallet1'),
        Index('fk_ledger_entry_money_transaction1_idx', 'money_transaction_id'),
        Index('fk_ledger_entry_wallet1_idx', 'wallet_id')
    )

    id_ledger_entry = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, nullable=False)
    money_transaction_id = Column(Integer, nullable=False)
    ledger_entry_type = Column(Enum('CREDIT', 'DEBIT'))
    ledger_entry_amount = Column(DECIMAL(20, 8))

    money_transaction = relationship('MoneyTransaction', back_populates='ledger_entry')
    wallet = relationship('Wallet', back_populates='ledger_entry')


class ManagementRule(Base):
    __tablename__ = 'management_rule'
    __table_args__ = (
        ForeignKeyConstraint(['rule_ref_org'], ['provider_organisation.idprovider_organisation'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_management_rule_1'),
        ForeignKeyConstraint(['rule_ref_provider'], ['product_provider.id_product_provider'], name='fk_management_rule_2'),
        ForeignKeyConstraint(['rule_ref_user'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_management_rule_3'),
        Index('fk_management_rule_1_idx', 'rule_ref_org'),
        Index('fk_management_rule_2_idx', 'rule_ref_provider'),
        Index('fk_management_rule_3_idx', 'rule_ref_user')
    )

    id_management_rule = Column(Integer, primary_key=True)
    rule_ref_org = Column(Integer)
    rule_ref_provider = Column(Integer)
    rule_ref_user = Column(Integer)
    management_rule_code = Column(Integer)
    management_rule_status = Column(Enum('PENDING', 'REJECTED', 'SUSPENDED', 'OBSOLETE', 'ACTIVE'), server_default=text("'PENDING'"))
    management_rule_expiry = Column(DateTime)

    provider_organisation = relationship('ProviderOrganisation', back_populates='management_rule')
    product_provider = relationship('ProductProvider', back_populates='management_rule')
    app_user = relationship('AppUser', back_populates='management_rule')
    role_invitation = relationship('RoleInvitation', back_populates='rule')


class Prescription(Base):
    __tablename__ = 'prescription'
    __table_args__ = (
        ForeignKeyConstraint(['diagnosis_id'], ['diagnosis.id_diagnosis'], name='fk_prescription_diagnosis1'),
        Index('fk_prescription_diagnosis1_idx', 'diagnosis_id')
    )

    id_prescription = Column(Integer, primary_key=True)
    diagnosis_id = Column(Integer)

    diagnosis = relationship('Diagnosis', back_populates='prescription')
    prescribed_item = relationship('PrescribedItem', back_populates='prescription')


class PresentedSymptom(Base):
    __tablename__ = 'presented_symptom'
    __table_args__ = (
        ForeignKeyConstraint(['presented_symptom_ref_symptom'], ['symptom.id_symptom'], name='fk_presented_symptom_1'),
        ForeignKeyConstraint(['presented_symptom_ref_symptoms_occurence'], ['symptoms_occurence.id_symptoms_occurence'], name='fk_presented_symptom_2'),
        Index('fk_presented_symptom_1_idx', 'presented_symptom_ref_symptom'),
        Index('fk_presented_symptom_2_idx', 'presented_symptom_ref_symptoms_occurence')
    )

    id_presented_symptom = Column(Integer, primary_key=True)
    presented_symptom_ref_symptoms_occurence = Column(Integer)
    presented_symptom_ref_symptom = Column(Integer)

    symptom = relationship('Symptom', back_populates='presented_symptom')
    symptoms_occurence = relationship('SymptomsOccurence', back_populates='presented_symptom')


class Product(Base):
    __tablename__ = 'product'
    __table_args__ = (
        ForeignKeyConstraint(['product_category_id'], ['product_category.id_product_category'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_2'),
        ForeignKeyConstraint(['product_origin_id'], ['iproduct.id_iproduct'], name='fk_product_4'),
        ForeignKeyConstraint(['product_owner'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_3'),
        ForeignKeyConstraint(['product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_1'),
        Index('fk_product_1_idx', 'product_provider_id'),
        Index('fk_product_2_idx', 'product_category_id'),
        Index('fk_product_3_idx', 'product_owner'),
        Index('fk_product_4_idx', 'product_origin_id')
    )

    id_product = Column(Integer, primary_key=True)
    product_name = Column(String(45))
    product_brand = Column(String(45))
    product_provider_id = Column(Integer)
    product_category_id = Column(Integer)
    product_barcode = Column(String(45))
    last_updated = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    created = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    product_description = Column(String(300))
    product_price = Column(Float(asdecimal=True), server_default=text("'0'"))
    product_base_price = Column(Float(asdecimal=True), server_default=text("'0'"))
    product_quantity = Column(Integer, server_default=text("'0'"))
    product_reserved_quantity = Column(Integer, server_default=text("'0'"))
    product_quantifier = Column(String(45))
    product_owner = Column(Integer)
    product_origin_id = Column(Integer)
    product_visibility = Column(Enum('VISIBLE', 'HIDDEN', 'DELETED'), server_default=text("'VISIBLE'"))

    product_category = relationship('ProductCategory', back_populates='product')
    product_origin = relationship('Iproduct', back_populates='product')
    app_user = relationship('AppUser', back_populates='product')
    product_provider = relationship('ProductProvider', back_populates='product')
    ordered_item = relationship('OrderedItem', back_populates='ordered_product')
    product_image = relationship('ProductImage', back_populates='product_ref')
    product_reaction = relationship('ProductReaction', back_populates='product')
    service_resource_requirement = relationship('ServiceResourceRequirement', back_populates='product')
    product_consumption = relationship('ProductConsumption', back_populates='consumed_product')


class ProvidedService(Base):
    __tablename__ = 'provided_service'
    __table_args__ = (
        ForeignKeyConstraint(['provided_service_category_id'], ['provided_service_category.provided_service_category_id'], ondelete='RESTRICT', onupdate='CASCADE', name='provided_service_ibfk_1'),
        ForeignKeyConstraint(['provided_service_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='provided_service_ibfk_2'),
        Index('idx_provided_service_active', 'provided_service_is_active', 'provided_service_deleted_at'),
        Index('idx_provided_service_category', 'provided_service_category_id'),
        Index('idx_provided_service_created_at', 'provided_service_created_at'),
        Index('idx_provided_service_name', 'provided_service_name'),
        Index('idx_provided_service_price_range', 'provided_service_base_price', 'provided_service_final_price'),
        Index('idx_provided_service_provider', 'provided_service_product_provider_id')
    )

    provided_service_id = Column(Integer, primary_key=True)
    provided_service_name = Column(String(255))
    provided_service_description = Column(Text)
    provided_service_category_id = Column(Integer)
    provided_service_product_provider_id = Column(Integer, comment='References i_product_provider.id_product_provider')
    provided_service_base_price = Column(DECIMAL(15, 4))
    provided_service_final_price = Column(DECIMAL(15, 4))
    provided_service_actual_duration = Column(DECIMAL(10, 2))
    provided_service_is_active = Column(TINYINT(1), server_default=text("'1'"))
    provided_service_pricing_config = Column(JSON)
    provided_service_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    provided_service_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    provided_service_deleted_at = Column(TIMESTAMP)

    provided_service_category = relationship('ProvidedServiceCategory', back_populates='provided_service')
    provided_service_product_provider = relationship('ProductProvider', back_populates='provided_service')
    ordered_service = relationship('OrderedService', back_populates='ordered_service_service')
    service_contribution = relationship('ServiceContribution', back_populates='provided_service')
    service_package_item = relationship('ServicePackageItem', back_populates='service_package_item_service')
    service_resource_requirement = relationship('ServiceResourceRequirement', back_populates='service_resource_requirement_service')
    service_staff_requirement = relationship('ServiceStaffRequirement', back_populates='service_staff_requirement_service')


class ProviderImage(Base):
    __tablename__ = 'provider_image'
    __table_args__ = (
        ForeignKeyConstraint(['provider_ref_id'], ['product_provider.id_product_provider'], name='fk_provider_image_1'),
        Index('fk_provider_image_1_idx', 'provider_ref_id')
    )

    id_provider_image = Column(Integer, primary_key=True)
    provider_image_url = Column(String(255))
    provider_ref_id = Column(Integer)

    provider_ref = relationship('ProductProvider', back_populates='provider_image')


class ProviderReaction(Base):
    __tablename__ = 'provider_reaction'
    __table_args__ = (
        ForeignKeyConstraint(['provider_reacting_user'], ['app_user.id_app_user'], name='fk_product_reaction_12'),
        ForeignKeyConstraint(['reacted_on_provider'], ['product_provider.id_product_provider'], name='fk_product_reaction_31'),
        Index('fk_product_reaction_1_idx', 'provider_reacting_user'),
        Index('fk_product_reaction_31_idx', 'reacted_on_provider')
    )

    id_provider_reaction = Column(Integer, primary_key=True)
    provider_reacting_user = Column(Integer)
    provider_reaction = Column(Enum('like', 'dislike', 'love', 'helpful', 'not_helpful', 'star'), server_default=text("'like'"))
    reacted_on_provider = Column(Integer)
    provider_reaction_value = Column(Float, server_default=text("'0'"))

    app_user = relationship('AppUser', back_populates='provider_reaction')
    product_provider = relationship('ProductProvider', back_populates='provider_reaction')


class RecipeContainsIngredient(Base):
    __tablename__ = 'recipe_contains_ingredient'
    __table_args__ = (
        ForeignKeyConstraint(['contained_ingredient_id'], ['ingredient.id_ingredient'], name='fk_recipe_contains_ingredient_2'),
        ForeignKeyConstraint(['containing_recipe_id'], ['recipe.id_recipe'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_recipe_contains_ingredient_1'),
        Index('fk_recipe_contains_ingredient_1_idx', 'containing_recipe_id'),
        Index('fk_recipe_contains_ingredient_2_idx', 'contained_ingredient_id')
    )

    idrecipe_contains_ingredient_id = Column(Integer, primary_key=True)
    containing_recipe_id = Column(Integer)
    contained_ingredient_id = Column(Integer)
    contained_quantity = Column(String(45))

    contained_ingredient = relationship('Ingredient', back_populates='recipe_contains_ingredient')
    containing_recipe = relationship('Recipe', back_populates='recipe_contains_ingredient')


class RecipeImage(Base):
    __tablename__ = 'recipe_image'
    __table_args__ = (
        ForeignKeyConstraint(['recipe_ref_id'], ['recipe.id_recipe'], name='fk_recipe_image_1'),
        Index('fk_recipe_image_1_idx', 'recipe_ref_id')
    )

    id_recipe_image = Column(Integer, primary_key=True)
    recipe_image_url = Column(String(255))
    recipe_ref_id = Column(Integer)

    recipe_ref = relationship('Recipe', back_populates='recipe_image')


class RecipeReaction(Base):
    __tablename__ = 'recipe_reaction'
    __table_args__ = (
        ForeignKeyConstraint(['reacted_on_recipe'], ['recipe.id_recipe'], name='fk_recipe_reaction_1'),
        ForeignKeyConstraint(['recipe_reacting_user'], ['app_user.id_app_user'], name='fk_product_reaction_10'),
        Index('fk_product_reaction_1_idx', 'recipe_reacting_user'),
        Index('fk_recipe_reaction_1_idx', 'reacted_on_recipe')
    )

    id_recipe_reaction = Column(Integer, primary_key=True)
    recipe_reacting_user = Column(Integer)
    recipe_reaction = Column(Enum('like', 'dislike', 'love', 'helpful', 'not_helpful', 'star'), server_default=text("'like'"))
    reacted_on_recipe = Column(Integer)

    recipe = relationship('Recipe', back_populates='recipe_reaction')
    app_user = relationship('AppUser', back_populates='recipe_reaction')


class ServicePackage(Base):
    __tablename__ = 'service_package'
    __table_args__ = (
        ForeignKeyConstraint(['service_package_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='service_package_ibfk_1'),
        Index('idx_service_package_active', 'service_package_is_active'),
        Index('idx_service_package_provider', 'service_package_product_provider_id'),
        Index('idx_service_package_validity', 'service_package_valid_from', 'service_package_valid_to')
    )

    service_package_id = Column(Integer, primary_key=True)
    service_package_name = Column(String(255))
    service_package_description = Column(Text)
    service_package_product_provider_id = Column(Integer)
    service_package_price = Column(DECIMAL(15, 4))
    service_package_discount_percentage = Column(DECIMAL(5, 2))
    service_package_is_active = Column(TINYINT(1), server_default=text("'1'"))
    service_package_valid_from = Column(Date)
    service_package_valid_to = Column(Date)
    service_package_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_package_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    service_package_product_provider = relationship('ProductProvider', back_populates='service_package')
    service_package_item = relationship('ServicePackageItem', back_populates='service_package_item_package')


class Message(Base):
    __tablename__ = 'message'
    __table_args__ = (
        ForeignKeyConstraint(['message_conversation_id'], ['conversation.id_conversation'], name='fk_message_convo'),
        Index('fk_message_1_idx', 'message_conversation_id')
    )

    id_message = Column(Integer, primary_key=True)
    message_content = Column(String(255))
    message_attached_url = Column(String(255))
    message_type = Column(Enum('text', 'image', 'file', 'notification', 'system', 'voice', 'video'), server_default=text("'text'"))
    message_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    message_delivered_at = Column(TIMESTAMP)
    message_read_at = Column(TIMESTAMP)
    message_conversation_id = Column(Integer)
    message_is_from_sender = Column(TINYINT)

    message_conversation = relationship('Conversation', back_populates='message')


class OrderedItem(Base):
    __tablename__ = 'ordered_item'
    __table_args__ = (
        ForeignKeyConstraint(['discount_id'], ['discount.id_discount'], name='fk_ordered_item_4'),
        ForeignKeyConstraint(['order_ref'], ['placed_order.id_placed_order'], name='fk_ordered_item_3'),
        ForeignKeyConstraint(['ordered_item_cart_ref'], ['cart.cart_id'], name='fk_ordered_item_2'),
        ForeignKeyConstraint(['ordered_product_id'], ['product.id_product'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_ordered_item_1'),
        Index('fk_ordered_item_1_idx', 'ordered_product_id'),
        Index('fk_ordered_item_2_idx', 'ordered_item_cart_ref'),
        Index('fk_ordered_item_3_idx', 'order_ref'),
        Index('fk_ordered_item_4_idx', 'discount_id')
    )

    id_ordered_item = Column(Integer, primary_key=True)
    ordered_product_id = Column(Integer)
    ordered_quantity = Column(Integer, server_default=text("'0'"))
    reserved_quantity = Column(Integer, server_default=text("'0'"))
    applied_vat = Column(Float(asdecimal=True))
    order_ref = Column(Integer)
    unit_price = Column(Float(asdecimal=True))
    product_discount = Column(Float(asdecimal=True))
    ordered_item_cart_ref = Column(Integer)
    ordered_item_delivery_status = Column(Enum('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'returned', 'partial'), server_default=text("'pending'"))
    ordered_item_delivery_fee = Column(Float(asdecimal=True), server_default=text("'0'"))
    ordered_item_last_mod = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    placed_order_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    discount_id = Column(Integer)

    discount = relationship('Discount', back_populates='ordered_item')
    placed_order = relationship('PlacedOrder', back_populates='ordered_item')
    cart = relationship('Cart', back_populates='ordered_item')
    ordered_product = relationship('Product', back_populates='ordered_item')


class OrderedService(Base):
    __tablename__ = 'ordered_service'
    __table_args__ = (
        ForeignKeyConstraint(['discount_id'], ['discount.id_discount'], name='fk_ordered_service_1'),
        ForeignKeyConstraint(['ordered_service_cart_id'], ['cart.cart_id'], ondelete='CASCADE', onupdate='CASCADE', name='ordered_service_ibfk_1'),
        ForeignKeyConstraint(['ordered_service_service_id'], ['provided_service.provided_service_id'], ondelete='RESTRICT', onupdate='CASCADE', name='ordered_service_ibfk_2'),
        Index('fk_ordered_service_1_idx', 'discount_id'),
        Index('idx_cart', 'ordered_service_cart_id'),
        Index('idx_service', 'ordered_service_service_id')
    )

    ordered_service_id = Column(Integer, primary_key=True)
    ordered_service_cart_id = Column(Integer)
    ordered_service_service_id = Column(Integer, comment='References provided_service')
    ordered_service_quantity = Column(Integer, server_default=text("'1'"))
    ordered_service_unit_price = Column(DECIMAL(15, 4))
    ordered_service_total_price = Column(DECIMAL(15, 4))
    ordered_service_notes = Column(Text)
    ordered_service_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    ordered_service_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    ordered_service_scheduled_at = Column(TIMESTAMP)
    ordered_service_delivery_fee = Column(Float(asdecimal=True), server_default=text("'0'"))
    ordered_service_delivery_status = Column(Enum('pending', 'processing', 'scheduled', 'in_progress', 'completed', 'cancelled', 'no_show'), server_default=text("'pending'"))
    discount_id = Column(Integer)
    service_discount = Column(Float(asdecimal=True))

    discount = relationship('Discount', back_populates='ordered_service')
    ordered_service_cart = relationship('Cart', back_populates='ordered_service')
    ordered_service_service = relationship('ProvidedService', back_populates='ordered_service')
    product_consumption = relationship('ProductConsumption', back_populates='consuming_service')


class PrescribedItem(Base):
    __tablename__ = 'prescribed_item'
    __table_args__ = (
        ForeignKeyConstraint(['iproduct_id'], ['iproduct.id_iproduct'], name='fk_table1_iproduct1'),
        ForeignKeyConstraint(['prescription_id'], ['prescription.id_prescription'], name='fk_table1_prescription1'),
        Index('fk_table1_iproduct1_idx', 'iproduct_id'),
        Index('fk_table1_prescription1_idx', 'prescription_id')
    )

    prescription_id = Column(Integer, primary_key=True, nullable=False)
    iproduct_id = Column(Integer, primary_key=True, nullable=False)
    prescribed_amount = Column(Float(asdecimal=True))
    prescribed_recurrence = Column(String(45))

    iproduct = relationship('Iproduct', back_populates='prescribed_item')
    prescription = relationship('Prescription', back_populates='prescribed_item')


class ProductImage(Base):
    __tablename__ = 'product_image'
    __table_args__ = (
        ForeignKeyConstraint(['product_ref_id'], ['product.id_product'], name='fk_product_image_1'),
        Index('fk_product_image_1_idx', 'product_ref_id')
    )

    id_product_image = Column(Integer, primary_key=True)
    product_image_url = Column(String(255))
    product_ref_id = Column(Integer)

    product_ref = relationship('Product', back_populates='product_image')


class ProductReaction(Base):
    __tablename__ = 'product_reaction'
    __table_args__ = (
        ForeignKeyConstraint(['product_reacting_user'], ['app_user.id_app_user'], name='fk_product_reaction_1'),
        ForeignKeyConstraint(['reacted_on_product'], ['product.id_product'], name='fk_product_reaction_3'),
        Index('fk_product_reaction_1_idx', 'product_reacting_user'),
        Index('fk_product_reaction_3_idx', 'reacted_on_product')
    )

    id_product_reaction = Column(Integer, primary_key=True)
    product_reacting_user = Column(Integer)
    product_reaction = Column(Enum('like', 'dislike', 'love', 'helpful', 'not_helpful', 'star'), server_default=text("'like'"))
    reacted_on_product = Column(Integer)
    product_reaction_value = Column(Float, server_default=text("'0'"))

    app_user = relationship('AppUser', back_populates='product_reaction')
    product = relationship('Product', back_populates='product_reaction')


class RoleInvitation(Base):
    __tablename__ = 'role_invitation'
    __table_args__ = (
        ForeignKeyConstraint(['app_user_id'], ['app_user.id_app_user'], name='fk_role_invitation_app_user1'),
        ForeignKeyConstraint(['notification_id'], ['notification.id_notification'], name='fk_role_invitation_notification1'),
        ForeignKeyConstraint(['organisation_id'], ['provider_organisation.idprovider_organisation'], name='fk_role_invitation_provider_organisation1'),
        ForeignKeyConstraint(['provider_id'], ['product_provider.id_product_provider'], name='fk_role_invitation_product_provider1'),
        ForeignKeyConstraint(['rule_id'], ['management_rule.id_management_rule'], name='fk_role_invitation_management_rule1'),
        Index('fk_role_invitation_app_user1_idx', 'app_user_id'),
        Index('fk_role_invitation_management_rule1_idx', 'rule_id'),
        Index('fk_role_invitation_notification1_idx', 'notification_id'),
        Index('fk_role_invitation_product_provider1_idx', 'provider_id'),
        Index('fk_role_invitation_provider_organisation1_idx', 'organisation_id')
    )

    id_role_invitation = Column(Integer, primary_key=True)
    provider_id = Column(Integer, nullable=False)
    app_user_id = Column(Integer, nullable=False)
    notification_id = Column(Integer)
    organisation_id = Column(Integer)
    rule_id = Column(Integer)
    invitation_status = Column(Enum('PENDING', 'REJECTED', 'EXPIRED', 'ACCEPTED'), server_default=text("'PENDING'"))
    invitation_expiry = Column(DateTime)

    app_user = relationship('AppUser', back_populates='role_invitation')
    notification = relationship('Notification', back_populates='role_invitation')
    organisation = relationship('ProviderOrganisation', back_populates='role_invitation')
    provider = relationship('ProductProvider', back_populates='role_invitation')
    rule = relationship('ManagementRule', back_populates='role_invitation')


class ServiceContribution(Base):
    __tablename__ = 'service_contribution'
    __table_args__ = (
        ForeignKeyConstraint(['service_contribution_org_ref'], ['provider_organisation.idprovider_organisation'], name='fk_service_contribution_2'),
        ForeignKeyConstraint(['service_contribution_person_ref'], ['person.id_person'], name='fk_service_contribution_4'),
        ForeignKeyConstraint(['service_contribution_provider_ref'], ['product_provider.id_product_provider'], name='fk_service_contribution_6'),
        ForeignKeyConstraint(['service_contribution_user_ref'], ['app_user.id_app_user'], name='fk_service_contribution_3'),
        ForeignKeyConstraint(['service_ref'], ['provided_service.provided_service_id'], name='fk_service_contribution_5'),
        Index('fk_service_contribution_2_idx', 'service_contribution_org_ref'),
        Index('fk_service_contribution_3_idx', 'service_contribution_user_ref'),
        Index('fk_service_contribution_4_idx', 'service_contribution_person_ref'),
        Index('fk_service_contribution_5_idx', 'service_ref'),
        Index('fk_service_contribution_6_idx', 'service_contribution_provider_ref')
    )

    id_service_contribution = Column(Integer, primary_key=True)
    service_contribution_duration = Column(String(45))
    service_contribution_price = Column(Float)
    service_contribution_currency = Column(String(45))
    service_contribution_org_ref = Column(Integer)
    service_contribution_user_ref = Column(Integer)
    service_contribution_person_ref = Column(Integer)
    service_ref = Column(Integer)
    service_contribution_start = Column(TIMESTAMP)
    service_contribution_provider_ref = Column(Integer)

    provider_organisation = relationship('ProviderOrganisation', back_populates='service_contribution')
    person = relationship('Person', back_populates='service_contribution')
    product_provider = relationship('ProductProvider', back_populates='service_contribution')
    app_user = relationship('AppUser', back_populates='service_contribution')
    provided_service = relationship('ProvidedService', back_populates='service_contribution')


class ServicePackageItem(Base):
    __tablename__ = 'service_package_item'
    __table_args__ = (
        ForeignKeyConstraint(['service_package_item_package_id'], ['service_package.service_package_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_package_item_ibfk_1'),
        ForeignKeyConstraint(['service_package_item_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_package_item_ibfk_2'),
        Index('idx_service_package_item_service', 'service_package_item_service_id'),
        Index('uk_package_service', 'service_package_item_package_id', 'service_package_item_service_id', unique=True)
    )

    service_package_item_id = Column(Integer, primary_key=True)
    service_package_item_package_id = Column(Integer)
    service_package_item_service_id = Column(Integer)
    service_package_item_sequence_order = Column(Integer, server_default=text("'1'"))
    service_package_item_quantity = Column(Integer, server_default=text("'1'"))
    service_package_item_notes = Column(Text)

    service_package_item_package = relationship('ServicePackage', back_populates='service_package_item')
    service_package_item_service = relationship('ProvidedService', back_populates='service_package_item')


class ServiceResourceRequirement(Base):
    __tablename__ = 'service_resource_requirement'
    __table_args__ = (
        ForeignKeyConstraint(['service_resource_requirement_product_ref'], ['product.id_product'], name='fk_service_resource_requirement_1'),
        ForeignKeyConstraint(['service_resource_requirement_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_resource_requirement_ibfk_1'),
        Index('fk_service_resource_requirement_1_idx', 'service_resource_requirement_product_ref'),
        Index('idx_resource_requirement_name', 'service_resource_requirement_name'),
        Index('idx_resource_requirement_service', 'service_resource_requirement_service_id'),
        Index('idx_resource_requirement_type', 'service_resource_requirement_type')
    )

    service_resource_requirement_id = Column(Integer, primary_key=True)
    service_resource_requirement_service_id = Column(Integer)
    service_resource_requirement_name = Column(String(255))
    service_resource_requirement_type = Column(String(100))
    service_resource_requirement_quantity = Column(Integer, server_default=text("'1'"))
    service_resource_requirement_cost_per_unit = Column(DECIMAL(15, 4))
    service_resource_requirement_is_consumable = Column(TINYINT(1), server_default=text("'0'"))
    service_resource_requirement_notes = Column(Text)
    service_resource_requirement_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_resource_requirement_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    service_resource_requirement_product_ref = Column(Integer)

    product = relationship('Product', back_populates='service_resource_requirement')
    service_resource_requirement_service = relationship('ProvidedService', back_populates='service_resource_requirement')
    product_consumption = relationship('ProductConsumption', back_populates='service_resource_requirement')


class ServiceStaffRequirement(Base):
    __tablename__ = 'service_staff_requirement'
    __table_args__ = (
        ForeignKeyConstraint(['service_staff_requirement_role'], ['staff_role.id_staff_role'], name='fk_service_staff_requirement_1'),
        ForeignKeyConstraint(['service_staff_requirement_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_staff_requirement_ibfk_1'),
        Index('idx_service_staff_requirement_role', 'service_staff_requirement_role'),
        Index('idx_service_staff_requirement_service', 'service_staff_requirement_service_id')
    )

    service_staff_requirement_id = Column(Integer, primary_key=True)
    service_staff_requirement_service_id = Column(Integer)
    service_staff_requirement_role = Column(Integer)
    service_staff_requirement_min_count = Column(Integer, server_default=text("'1'"))
    service_staff_requirement_max_count = Column(Integer)
    service_staff_requirement_hourly_rate = Column(DECIMAL(15, 4))
    service_staff_requirement_allocated_hours = Column(DECIMAL(5, 2))
    service_staff_requirement_notes = Column(Text)
    service_staff_requirement_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_staff_requirement_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    staff_role = relationship('StaffRole', back_populates='service_staff_requirement')
    service_staff_requirement_service = relationship('ProvidedService', back_populates='service_staff_requirement')


class ProductConsumption(Base):
    __tablename__ = 'product_consumption'
    __table_args__ = (
        ForeignKeyConstraint(['consumed_product_id'], ['product.id_product'], name='fk_product_consumption_product1'),
        ForeignKeyConstraint(['consuming_service_id'], ['ordered_service.ordered_service_id'], name='fk_product_consumption_ordered_service1'),
        ForeignKeyConstraint(['resource_req_ref'], ['service_resource_requirement.service_resource_requirement_id'], name='fk_product_consumption_service_resource_requirement1'),
        Index('fk_product_consumption_ordered_service1_idx', 'consuming_service_id'),
        Index('fk_product_consumption_product1_idx', 'consumed_product_id'),
        Index('fk_product_consumption_service_resource_requirement1_idx', 'resource_req_ref')
    )

    id_product_consumption = Column(Integer, primary_key=True)
    resource_req_ref = Column(Integer)
    consuming_service_id = Column(Integer)
    consumed_product_id = Column(Integer)
    product_reserved_quantity = Column(Integer)

    consumed_product = relationship('Product', back_populates='product_consumption')
    consuming_service = relationship('OrderedService', back_populates='product_consumption')
    service_resource_requirement = relationship('ServiceResourceRequirement', back_populates='product_consumption')
