{#
    classify_trend(current_col, previous_col, threshold=0.05)

    Returns a CASE expression that classifies the trend between two values
    into one of five categories based on the percentage change.

    Args:
        current_col: The current period's value column.
        previous_col: The previous period's value column.
        threshold: The percentage change threshold for classification (default: 0.05 = 5%).

    Categories:
        - 'strong_growth':  change > 2 * threshold
        - 'growth':         change > threshold
        - 'stable':         change between -threshold and threshold
        - 'decline':        change < -threshold
        - 'strong_decline': change < -2 * threshold

    Usage:
        {{ classify_trend('current_revenue', 'previous_revenue') }}
        {{ classify_trend('this_month', 'last_month', threshold=0.10) }}

    Output:
        case
            when (current_revenue - previous_revenue)::numeric / nullif(abs(previous_revenue), 0) > 0.10 then 'strong_growth'
            when ... > 0.05 then 'growth'
            when ... < -0.10 then 'strong_decline'
            when ... < -0.05 then 'decline'
            else 'stable'
        end
#}

{% macro classify_trend(current_col, previous_col, threshold=0.05) -%}
    case
        when {{ previous_col }} is null or {{ previous_col }} = 0 then 'no_comparison'
        when ({{ current_col }} - {{ previous_col }})::numeric / abs({{ previous_col }}) > {{ 2 * threshold }} then 'strong_growth'
        when ({{ current_col }} - {{ previous_col }})::numeric / abs({{ previous_col }}) > {{ threshold }} then 'growth'
        when ({{ current_col }} - {{ previous_col }})::numeric / abs({{ previous_col }}) < {{ -2 * threshold }} then 'strong_decline'
        when ({{ current_col }} - {{ previous_col }})::numeric / abs({{ previous_col }}) < {{ -1 * threshold }} then 'decline'
        else 'stable'
    end
{%- endmacro %}
