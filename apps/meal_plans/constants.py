# Meal Type Configuration Constants
# Replaces the MealTypeConfig database table

MEAL_TYPES = {
    'Bữa sáng': {
        'label': 'Bữa sáng',
        'badge_class': 'bg-warning text-dark',
        'sort_order': 1,
        'is_active': True,
    },
    'Bữa trưa': {
        'label': 'Bữa trưa',
        'badge_class': 'bg-danger text-white',
        'sort_order': 2,
        'is_active': True,
    },
    'Bữa tối': {
        'label': 'Bữa tối',
        'badge_class': 'bg-info text-white',
        'sort_order': 3,
        'is_active': True,
    },
    'Bữa phụ': {
        'label': 'Bữa phụ',
        'badge_class': 'bg-secondary text-white',
        'sort_order': 4,
        'is_active': True,
    },
}


def get_meal_type_configs(active_only=True):
    """Get meal type configurations as a list of dicts"""
    configs = []
    for meal_type, config in MEAL_TYPES.items():
        if active_only and not config.get('is_active', True):
            continue
        configs.append({
            'meal_type': meal_type,
            'label': config['label'],
            'badge_class': config['badge_class'],
            'sort_order': config['sort_order'],
            'is_active': config['is_active'],
        })
    # Sort by sort_order
    return sorted(configs, key=lambda x: x['sort_order'])


def get_meal_type_choices(active_only=True):
    """Get meal type choices for form select"""
    return [(item['meal_type'], item['label']) for item in get_meal_type_configs(active_only=active_only)]


def get_meal_type_color_map(active_only=True):
    """Get mapping of meal_type -> badge_class"""
    return {
        item['meal_type']: item['badge_class']
        for item in get_meal_type_configs(active_only=active_only)
    }


def get_meal_type_label(meal_type: str, active_only=True):
    """Get label for a specific meal type"""
    config = MEAL_TYPES.get(meal_type, {})
    if active_only and not config.get('is_active', True):
        return None
    return config.get('label', meal_type)


def is_valid_meal_type(meal_type: str, active_only=True):
    """Check if a meal type is valid"""
    config = MEAL_TYPES.get(meal_type, {})
    if active_only:
        return config.get('is_active', False)
    return meal_type in MEAL_TYPES
