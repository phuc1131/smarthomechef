-- =========================================
-- CANONICAL DATABASE SCHEMA (Current Project State)
-- Generated on: 2026-05-10T14:16:02.285108
-- Source: current project tables and migrations snapshot
-- =========================================

-- =====================
-- TABLE: account_emailaddress
-- =====================
CREATE TABLE IF NOT EXISTS account_emailaddress (
id integer  NOT NULL,
email character varying  NOT NULL,
verified boolean  NOT NULL,
primary boolean  NOT NULL,
user_id integer  NOT NULL
);

-- =====================
-- TABLE: account_emailconfirmation
-- =====================
CREATE TABLE IF NOT EXISTS account_emailconfirmation (
id integer  NOT NULL,
created timestamp with time zone  NOT NULL,
sent timestamp with time zone,
key character varying  NOT NULL,
email_address_id integer  NOT NULL
);

-- =====================
-- TABLE: ai_recommendations
-- =====================
CREATE TABLE IF NOT EXISTS ai_recommendations (
id bigint DEFAULT nextval('ai_recommendations_id_seq'::regclass) NOT NULL,
account_id bigint,
food_id bigint,
score numeric,
budget_match_score numeric,
estimated_cost numeric,
reason text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: auth_group
-- =====================
CREATE TABLE IF NOT EXISTS auth_group (
id integer  NOT NULL,
name character varying  NOT NULL
);

-- =====================
-- TABLE: auth_group_permissions
-- =====================
CREATE TABLE IF NOT EXISTS auth_group_permissions (
id bigint  NOT NULL,
group_id integer  NOT NULL,
permission_id integer  NOT NULL
);

-- =====================
-- TABLE: auth_permission
-- =====================
CREATE TABLE IF NOT EXISTS auth_permission (
id integer  NOT NULL,
name character varying  NOT NULL,
content_type_id integer  NOT NULL,
codename character varying  NOT NULL
);

-- =====================
-- TABLE: auth_user
-- =====================
CREATE TABLE IF NOT EXISTS auth_user (
id integer  NOT NULL,
password character varying  NOT NULL,
last_login timestamp with time zone  NOT NULL,
is_superuser boolean  NOT NULL,
username character varying  NOT NULL,
first_name character varying  NOT NULL,
last_name character varying  NOT NULL,
email character varying  NOT NULL,
is_staff boolean  NOT NULL,
is_active boolean  NOT NULL,
date_joined timestamp with time zone  NOT NULL
);

-- =====================
-- TABLE: auth_user_groups
-- =====================
CREATE TABLE IF NOT EXISTS auth_user_groups (
id bigint  NOT NULL,
user_id integer  NOT NULL,
group_id integer  NOT NULL
);

-- =====================
-- TABLE: auth_user_user_permissions
-- =====================
CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
id bigint  NOT NULL,
user_id integer  NOT NULL,
permission_id integer  NOT NULL
);

-- =====================
-- TABLE: chat_messages
-- =====================
CREATE TABLE IF NOT EXISTS chat_messages (
id bigint DEFAULT nextval('chat_messages_id_seq'::regclass) NOT NULL,
session_id bigint,
role character varying,
content text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: chat_response_caches
-- =====================
CREATE TABLE IF NOT EXISTS chat_response_caches (
id bigint DEFAULT nextval('chat_response_caches_id_seq'::regclass) NOT NULL,
normalized_query text,
original_query text,
response text,
usage_count integer DEFAULT 0,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: chat_sessions
-- =====================
CREATE TABLE IF NOT EXISTS chat_sessions (
id bigint DEFAULT nextval('chat_sessions_id_seq'::regclass) NOT NULL,
account_id bigint,
title character varying,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
missing_fields jsonb,
ask_count integer DEFAULT 0,
current_intent_id integer,
filled_fields jsonb,
updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: chat_summaries
-- =====================
CREATE TABLE IF NOT EXISTS chat_summaries (
id bigint DEFAULT nextval('chat_summaries_id_seq'::regclass) NOT NULL,
session_id bigint,
summary text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: daily_nutrition_summary
-- =====================
CREATE TABLE IF NOT EXISTS daily_nutrition_summary (
id bigint DEFAULT nextval('daily_nutrition_summary_id_seq'::regclass) NOT NULL,
account_id bigint,
date date,
total_calories numeric,
total_protein numeric,
total_carbs numeric,
total_fat numeric
);

-- =====================
-- TABLE: disease_nutrition_rules
-- =====================
CREATE TABLE IF NOT EXISTS disease_nutrition_rules (
id integer DEFAULT nextval('disease_nutrition_rules_id_seq'::regclass) NOT NULL,
disease_id integer,
nutrient character varying,
rule_type character varying,
threshold_value numeric
);

-- =====================
-- TABLE: diseases
-- =====================
CREATE TABLE IF NOT EXISTS diseases (
id integer DEFAULT nextval('diseases_id_seq'::regclass) NOT NULL,
name character varying  NOT NULL,
description text
);

-- =====================
-- TABLE: django_admin_log
-- =====================
CREATE TABLE IF NOT EXISTS django_admin_log (
id integer  NOT NULL,
action_time timestamp with time zone  NOT NULL,
object_id text,
object_repr character varying  NOT NULL,
action_flag smallint  NOT NULL,
change_message text  NOT NULL,
content_type_id integer,
user_id integer  NOT NULL
);

-- =====================
-- TABLE: django_content_type
-- =====================
CREATE TABLE IF NOT EXISTS django_content_type (
id integer  NOT NULL,
name character varying DEFAULT 'unknown'::character varying NOT NULL,
app_label character varying  NOT NULL,
model character varying  NOT NULL
);

-- =====================
-- TABLE: django_migrations
-- =====================
CREATE TABLE IF NOT EXISTS django_migrations (
id bigint  NOT NULL,
app character varying  NOT NULL,
name character varying  NOT NULL,
applied timestamp with time zone  NOT NULL
);

-- =====================
-- TABLE: django_session
-- =====================
CREATE TABLE IF NOT EXISTS django_session (
session_key character varying  NOT NULL,
session_data text  NOT NULL,
expire_date timestamp with time zone  NOT NULL
);

-- =====================
-- TABLE: django_site
-- =====================
CREATE TABLE IF NOT EXISTS django_site (
id integer  NOT NULL,
domain character varying  NOT NULL,
name character varying  NOT NULL
);

-- =====================
-- TABLE: food_categories
-- =====================
CREATE TABLE IF NOT EXISTS food_categories (
id integer DEFAULT nextval('food_categories_id_seq'::regclass) NOT NULL,
name character varying  NOT NULL
);

-- =====================
-- TABLE: food_ingredients
-- =====================
CREATE TABLE IF NOT EXISTS food_ingredients (
food_id bigint  NOT NULL,
ingredient_id bigint  NOT NULL,
quantity numeric,
id bigint DEFAULT nextval('food_ingredients_id_seq'::regclass) NOT NULL
);

-- =====================
-- TABLE: food_popularity
-- =====================
CREATE TABLE IF NOT EXISTS food_popularity (
food_id bigint  NOT NULL,
view_count integer DEFAULT 0,
click_count integer DEFAULT 0,
like_count integer DEFAULT 0,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
id bigint DEFAULT nextval('food_popularity_id_seq'::regclass) NOT NULL
);

-- =====================
-- TABLE: food_recipes
-- =====================
CREATE TABLE IF NOT EXISTS food_recipes (
id bigint DEFAULT nextval('food_recipes_id_seq'::regclass) NOT NULL,
food_id bigint,
title character varying,
summary text,
instructions text,
ingredients_json jsonb,
nutrition_json jsonb,
source_url text,
image_url text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: foods
-- =====================
CREATE TABLE IF NOT EXISTS foods (
id bigint DEFAULT nextval('foods_id_seq'::regclass) NOT NULL,
name character varying  NOT NULL,
normalized_name character varying,
category_id integer,
calories numeric DEFAULT 0,
protein numeric DEFAULT 0,
carbs numeric DEFAULT 0,
fat numeric DEFAULT 0,
fiber numeric DEFAULT 0,
is_vegetarian boolean DEFAULT false,
is_diabetes_friendly boolean DEFAULT false,
is_weight_loss_friendly boolean DEFAULT false,
description text,
image_url text,
search_vector tsvector,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
sugar double precision,
sodium double precision,
cholesterol double precision,
vitamin_a double precision,
vitamin_c double precision,
calcium double precision,
iron double precision,
tags jsonb DEFAULT '[]'::jsonb
);

-- =====================
-- TABLE: ingredient_nutrition
-- =====================
CREATE TABLE IF NOT EXISTS ingredient_nutrition (
ingredient_id bigint  NOT NULL,
calories numeric DEFAULT 0,
protein numeric DEFAULT 0,
carbs numeric DEFAULT 0,
fat numeric DEFAULT 0,
fiber numeric DEFAULT 0,
id bigint DEFAULT nextval('ingredient_nutrition_id_seq'::regclass) NOT NULL
);

-- =====================
-- TABLE: ingredient_prices
-- =====================
CREATE TABLE IF NOT EXISTS ingredient_prices (
id bigint DEFAULT nextval('ingredient_prices_id_seq'::regclass) NOT NULL,
ingredient_id bigint,
price_per_unit numeric  NOT NULL,
unit_type character varying DEFAULT 'kg'::character varying,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: ingredients
-- =====================
CREATE TABLE IF NOT EXISTS ingredients (
id bigint DEFAULT nextval('ingredients_id_seq'::regclass) NOT NULL,
name character varying  NOT NULL,
normalized_name character varying,
is_deleted boolean DEFAULT false
);

-- =====================
-- TABLE: intent_embeddings
-- =====================
CREATE TABLE IF NOT EXISTS intent_embeddings (
id bigint DEFAULT nextval('intent_embeddings_id_seq'::regclass) NOT NULL,
intent_name character varying,
embedding_vector jsonb,
source_type character varying,
confidence numeric,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: intents
-- =====================
CREATE TABLE IF NOT EXISTS intents (
id integer DEFAULT nextval('intents_id_seq'::regclass) NOT NULL,
name character varying,
description text,
required_fields jsonb,
topic character varying
);

-- =====================
-- TABLE: meal_plans
-- =====================
CREATE TABLE IF NOT EXISTS meal_plans (
id bigint DEFAULT nextval('meal_plans_id_seq'::regclass) NOT NULL,
account_id bigint,
food_id bigint,
date date,
meal_type character varying,
servings numeric DEFAULT 1,
notes text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: message_intents
-- =====================
CREATE TABLE IF NOT EXISTS message_intents (
id bigint DEFAULT nextval('message_intents_id_seq'::regclass) NOT NULL,
message_id bigint,
intent_id integer,
confidence numeric
);

-- =====================
-- TABLE: model_metadata
-- =====================
CREATE TABLE IF NOT EXISTS model_metadata (
id integer DEFAULT nextval('model_metadata_id_seq'::regclass) NOT NULL,
model_name character varying,
version character varying,
description text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: nutrition_logs
-- =====================
CREATE TABLE IF NOT EXISTS nutrition_logs (
id bigint DEFAULT nextval('nutrition_logs_id_seq'::regclass) NOT NULL,
account_id bigint,
food_id bigint,
date date,
meal_type character varying,
servings numeric DEFAULT 1,
total_calories numeric,
total_protein numeric,
total_carbs numeric,
total_fat numeric,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: patterns
-- =====================
CREATE TABLE IF NOT EXISTS patterns (
id integer DEFAULT nextval('patterns_id_seq'::regclass) NOT NULL,
intent_id integer,
text text
);

-- =====================
-- TABLE: recommendation_log
-- =====================
CREATE TABLE IF NOT EXISTS recommendation_log (
id bigint DEFAULT nextval('recommendation_log_id_seq'::regclass) NOT NULL,
account_id bigint,
food_id bigint,
score numeric,
reason text,
model_version character varying,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: search_events
-- =====================
CREATE TABLE IF NOT EXISTS search_events (
id bigint DEFAULT nextval('search_events_id_seq'::regclass) NOT NULL,
account_id bigint,
query_text text,
normalized_query text,
result_count integer,
clicked_food_id bigint,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: socialaccount_socialaccount
-- =====================
CREATE TABLE IF NOT EXISTS socialaccount_socialaccount (
id integer  NOT NULL,
provider character varying  NOT NULL,
uid character varying  NOT NULL,
last_login timestamp with time zone  NOT NULL,
date_joined timestamp with time zone  NOT NULL,
extra_data jsonb  NOT NULL,
user_id integer  NOT NULL
);

-- =====================
-- TABLE: socialaccount_socialapp
-- =====================
CREATE TABLE IF NOT EXISTS socialaccount_socialapp (
id integer  NOT NULL,
provider character varying  NOT NULL,
name character varying  NOT NULL,
client_id character varying  NOT NULL,
secret character varying  NOT NULL,
key character varying  NOT NULL,
provider_id character varying  NOT NULL,
settings jsonb  NOT NULL
);

-- =====================
-- TABLE: socialaccount_socialapp_sites
-- =====================
CREATE TABLE IF NOT EXISTS socialaccount_socialapp_sites (
id bigint  NOT NULL,
socialapp_id integer  NOT NULL,
site_id integer  NOT NULL
);

-- =====================
-- TABLE: socialaccount_socialtoken
-- =====================
CREATE TABLE IF NOT EXISTS socialaccount_socialtoken (
id integer  NOT NULL,
token text  NOT NULL,
token_secret text  NOT NULL,
expires_at timestamp with time zone,
account_id integer  NOT NULL,
app_id integer
);

-- =====================
-- TABLE: unit_conversions
-- =====================
CREATE TABLE IF NOT EXISTS unit_conversions (
id bigint DEFAULT nextval('unit_conversions_id_seq'::regclass) NOT NULL,
ingredient_id bigint,
from_unit character varying,
conversion_factor numeric
);

-- =====================
-- TABLE: user_behavior_log
-- =====================
CREATE TABLE IF NOT EXISTS user_behavior_log (
id bigint DEFAULT nextval('user_behavior_log_id_seq'::regclass) NOT NULL,
account_id bigint,
action_type character varying,
target_type character varying,
target_id bigint,
metadata jsonb,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: user_diseases
-- =====================
CREATE TABLE IF NOT EXISTS user_diseases (
account_id bigint  NOT NULL,
disease_id integer  NOT NULL,
severity character varying,
id bigint DEFAULT nextval('user_diseases_id_seq'::regclass) NOT NULL
);

-- =====================
-- TABLE: user_feedback
-- =====================
CREATE TABLE IF NOT EXISTS user_feedback (
id bigint DEFAULT nextval('user_feedback_id_seq'::regclass) NOT NULL,
account_id bigint,
food_id bigint,
rating integer,
liked boolean,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: user_goals
-- =====================
CREATE TABLE IF NOT EXISTS user_goals (
id bigint DEFAULT nextval('user_goals_id_seq'::regclass) NOT NULL,
account_id bigint,
goal_type character varying,
target_weight numeric,
daily_calorie_target integer,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- TABLE: user_preference_profiles
-- =====================
CREATE TABLE IF NOT EXISTS user_preference_profiles (
account_id bigint  NOT NULL,
preferred_macros jsonb,
preferred_categories jsonb,
preferred_keywords jsonb,
avoided_keywords jsonb,
healthy_score numeric DEFAULT 0,
unhealthy_score numeric DEFAULT 0,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
id bigint DEFAULT nextval('user_preference_profiles_id_seq'::regclass) NOT NULL
);

-- =====================
-- TABLE: user_profiles
-- =====================
CREATE TABLE IF NOT EXISTS user_profiles (
id bigint DEFAULT nextval('user_profiles_id_seq'::regclass) NOT NULL,
account_id bigint,
name character varying,
age integer,
gender character varying,
height numeric,
weight numeric,
activity_level character varying,
bmi numeric,
daily_calorie_target integer,
health_goal text,
medical_conditions text,
dietary_preferences text,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
budget_limit numeric
);

-- =====================
-- TABLE: users
-- =====================
CREATE TABLE IF NOT EXISTS users (
id bigint DEFAULT nextval('users_id_seq'::regclass) NOT NULL,
username character varying  NOT NULL,
email character varying,
password_hash text  NOT NULL,
role character varying DEFAULT 'user'::character varying,
is_active boolean DEFAULT true,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

