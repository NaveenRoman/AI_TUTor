from datetime import date

def has_active_subscription(institution):
    if not institution.is_active:
        return False

    if institution.subscription_end and institution.subscription_end < date.today():
        return False

    return True


def is_feature_allowed(institution, feature_name):

    plan = institution.plan

    feature_matrix = {
        "admin_dashboard": ["pro", "enterprise"],
        "weak_topics": ["pro", "enterprise"],
        "pdf_export": ["pro", "enterprise"],
        "batch_filtering": ["enterprise"],
        "placement_prediction": ["enterprise"],
    }

    allowed_plans = feature_matrix.get(feature_name, [])

    return plan in allowed_plans
