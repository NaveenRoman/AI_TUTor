def is_company_feature_allowed(company, feature):

    limits = {
        "free": {
            "max_filters": 5,
            "view_transcripts": False
        },
        "pro": {
            "max_filters": 50,
            "view_transcripts": True
        },
        "enterprise": {
            "max_filters": 9999,
            "view_transcripts": True
        }
    }

    return limits.get(company.plan, {}).get(feature, False)
