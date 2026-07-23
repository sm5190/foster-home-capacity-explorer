PRAGMA foreign_keys = ON;


CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);


CREATE TABLE statewide_summary (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    reporting_cutoff TEXT NOT NULL,
    observation_start TEXT NOT NULL,

    children_currently_in_care INTEGER NOT NULL
        CHECK (children_currently_in_care >= 0),

    current_kin_placements INTEGER NOT NULL
        CHECK (current_kin_placements >= 0),

    current_foster_home_placements INTEGER NOT NULL
        CHECK (current_foster_home_placements >= 0),

    current_nonfamily_placements INTEGER NOT NULL
        CHECK (current_nonfamily_placements >= 0),

    current_foster_homes INTEGER NOT NULL
        CHECK (current_foster_homes >= 0),

    homes_with_current_placement INTEGER NOT NULL
        CHECK (homes_with_current_placement >= 0),

    homes_with_recent_activity INTEGER NOT NULL
        CHECK (homes_with_recent_activity >= 0),

    homes_without_recent_activity INTEGER NOT NULL
        CHECK (homes_without_recent_activity >= 0),

    local_foster_placements INTEGER NOT NULL
        CHECK (local_foster_placements >= 0),

    out_of_county_foster_placements INTEGER NOT NULL
        CHECK (out_of_county_foster_placements >= 0),

    local_placement_rate REAL
        CHECK (
            local_placement_rate IS NULL
            OR local_placement_rate BETWEEN 0 AND 1
        ),

    median_observed_active_day_rate REAL
        CHECK (
            median_observed_active_day_rate IS NULL
            OR median_observed_active_day_rate BETWEEN 0 AND 1
        )
);


CREATE TABLE county_summary (
    county_slug TEXT PRIMARY KEY,
    county_name TEXT NOT NULL UNIQUE,

    children_currently_in_care INTEGER NOT NULL
        CHECK (children_currently_in_care >= 0),

    current_foster_homes INTEGER NOT NULL
        CHECK (current_foster_homes >= 0),

    children_per_current_home REAL
        CHECK (
            children_per_current_home IS NULL
            OR children_per_current_home >= 0
        ),

    current_foster_placements INTEGER NOT NULL
        CHECK (current_foster_placements >= 0),

    local_foster_placements INTEGER NOT NULL
        CHECK (local_foster_placements >= 0),

    out_of_county_foster_placements INTEGER NOT NULL
        CHECK (out_of_county_foster_placements >= 0),

    local_placement_rate REAL
        CHECK (
            local_placement_rate IS NULL
            OR local_placement_rate BETWEEN 0 AND 1
        ),

    homes_with_current_placement INTEGER NOT NULL
        CHECK (homes_with_current_placement >= 0),

    homes_with_recent_activity INTEGER NOT NULL
        CHECK (homes_with_recent_activity >= 0),

    homes_without_recent_activity INTEGER NOT NULL
        CHECK (homes_without_recent_activity >= 0),

    median_observed_active_day_rate REAL
        CHECK (
            median_observed_active_day_rate IS NULL
            OR median_observed_active_day_rate BETWEEN 0 AND 1
        ),

    renewals_within_90_days INTEGER NOT NULL
        CHECK (renewals_within_90_days >= 0),

    recruitment_level TEXT NOT NULL
        CHECK (
            recruitment_level IN (
                'higher',
                'possible',
                'review',
                'limited'
            )
        ),

    recruitment_signal_count INTEGER NOT NULL
        CHECK (recruitment_signal_count BETWEEN 0 AND 3),

    engagement_level TEXT NOT NULL
        CHECK (
            engagement_level IN (
                'higher',
                'possible',
                'review',
                'limited'
            )
        ),

    engagement_signal_count INTEGER NOT NULL
        CHECK (engagement_signal_count BETWEEN 0 AND 3),

    primary_opportunity TEXT NOT NULL
        CHECK (
            primary_opportunity IN (
                'recruitment',
                'engagement',
                'both',
                'review'
            )
        ),

    limited_data INTEGER NOT NULL
        CHECK (limited_data IN (0, 1))
);


CREATE TABLE county_age_alignment (
    county_slug TEXT NOT NULL,

    age_band TEXT NOT NULL
        CHECK (
            age_band IN (
                '0-5',
                '6-12',
                '13-17',
                'unknown'
            )
        ),

    current_children INTEGER NOT NULL
        CHECK (current_children >= 0),

    preference_matching_homes INTEGER NOT NULL
        CHECK (preference_matching_homes >= 0),

    children_per_matching_home REAL
        CHECK (
            children_per_matching_home IS NULL
            OR children_per_matching_home >= 0
        ),

    limited_data INTEGER NOT NULL
        CHECK (limited_data IN (0, 1)),

    recruitment_evidence INTEGER NOT NULL
        CHECK (recruitment_evidence IN (0, 1)),

    statewide_p75_threshold REAL
        CHECK (
            statewide_p75_threshold IS NULL
            OR statewide_p75_threshold >= 0
        ),

    PRIMARY KEY (
        county_slug,
        age_band
    ),

    FOREIGN KEY (county_slug)
        REFERENCES county_summary(county_slug)
        ON DELETE CASCADE,

    CHECK (
        age_band != 'unknown'
        OR (
            preference_matching_homes = 0
            AND children_per_matching_home IS NULL
            AND limited_data = 1
            AND recruitment_evidence = 0
            AND statewide_p75_threshold IS NULL
        )
    ),

    CHECK (
        age_band = 'unknown'
        OR (
            (
                preference_matching_homes = 0
                AND children_per_matching_home IS NULL
            )
            OR (
                preference_matching_homes > 0
                AND children_per_matching_home IS NOT NULL
            )
        )
    ),

    CHECK (
        recruitment_evidence = 0
        OR (
            age_band != 'unknown'
            AND limited_data = 0
            AND children_per_matching_home IS NOT NULL
            AND statewide_p75_threshold IS NOT NULL
            AND children_per_matching_home
                >= statewide_p75_threshold
        )
    )
);


CREATE TABLE county_placement_flow (
    origin_county_slug TEXT NOT NULL,
    destination_county_name TEXT NOT NULL,

    placement_count INTEGER NOT NULL
        CHECK (placement_count >= 0),

    placement_share REAL NOT NULL
        CHECK (placement_share BETWEEN 0 AND 1),

    is_local INTEGER NOT NULL
        CHECK (is_local IN (0, 1)),

    PRIMARY KEY (
        origin_county_slug,
        destination_county_name
    ),

    FOREIGN KEY (origin_county_slug)
        REFERENCES county_summary(county_slug)
        ON DELETE CASCADE
);


CREATE TABLE county_signal (
    county_slug TEXT NOT NULL,

    focus TEXT NOT NULL
        CHECK (
            focus IN (
                'recruitment',
                'engagement'
            )
        ),

    signal_code TEXT NOT NULL,
    signal_value REAL,
    threshold_value REAL,

    PRIMARY KEY (
        county_slug,
        focus,
        signal_code
    ),

    FOREIGN KEY (county_slug)
        REFERENCES county_summary(county_slug)
        ON DELETE CASCADE
);


CREATE TABLE county_investigation_question (
    county_slug TEXT NOT NULL,

    display_order INTEGER NOT NULL
        CHECK (display_order BETWEEN 1 AND 5),

    question_text TEXT NOT NULL
        CHECK (LENGTH(TRIM(question_text)) > 0),

    PRIMARY KEY (
        county_slug,
        display_order
    ),

    FOREIGN KEY (county_slug)
        REFERENCES county_summary(county_slug)
        ON DELETE CASCADE
);

CREATE INDEX idx_county_recruitment_priority
ON county_summary (
    recruitment_signal_count DESC,
    children_per_current_home DESC
);


CREATE INDEX idx_county_engagement_priority
ON county_summary (
    engagement_signal_count DESC,
    homes_without_recent_activity DESC
);


CREATE INDEX idx_county_flow_origin_count
ON county_placement_flow (
    origin_county_slug,
    placement_count DESC
);


CREATE INDEX idx_county_age_band
ON county_age_alignment (
    age_band,
    children_per_matching_home DESC
);