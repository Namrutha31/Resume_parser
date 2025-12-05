from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
# --- NEW: Experience Calculation Function (from your input) ---
def calculate_total_experience_unique(experience_data):
    if not experience_data:
        return 0.0

    total_months = 0
    current_dt = dt.now()
    intervals = []

    date_formats_to_try = [
        "%m/%Y", "%b %Y", "%B %Y", "%m-%Y", "%b-%Y", "%B-%Y",
        "%Y/%m", "%Y-%m" 
    ]

    for job in experience_data:
        # Ensure start_date and end_date keys exist
        if "start_date" not in job or "end_date" not in job:
            continue

        start_date_str = job["start_date"]
        end_date_str = job["end_date"]
        start_dt_obj = None

        # Parse start_date
        parsed_start = False
        for fmt in date_formats_to_try:
            try:
                start_dt_obj = dt.strptime(start_date_str, fmt)
                parsed_start = True
                break
            except (ValueError, TypeError):
                continue
        if not parsed_start:
            # st.warning(f"Could not parse start_date: '{start_date_str}'. Skipping job.")
            continue
        
        # Parse end_date
        end_dt_obj = None
        if end_date_str and end_date_str.lower().strip() in ['present', 'current']:
            end_dt_obj = current_dt
        else:
            parsed_end = False
            for fmt in date_formats_to_try:
                try:
                    # To make "Jan 2023 - Jan 2023" count as 1 month, treat end date as end of that month
                    end_dt_obj = dt.strptime(end_date_str, fmt) + relativedelta(months=1)
                    parsed_end = True
                    break
                except (ValueError, TypeError):
                    continue
            if not parsed_end:
                # st.warning(f"Could not parse end_date: '{end_date_str}'. Skipping job.")
                continue

        if end_dt_obj > start_dt_obj:
            intervals.append((start_dt_obj, end_dt_obj))

    if not intervals:
        return 0.0

    # Sort and merge intervals
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current_start, current_end in intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start < last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    # Calculate total months from merged intervals
    for start, end in merged:
        delta = relativedelta(end, start)
        total_months += delta.years * 12 + delta.months

    return round(total_months / 12, 2)

def format_experience(total_years_float):
    """Formats float years into a 'X years, Y months' string."""
    if not isinstance(total_years_float, (int, float)) or total_years_float <= 0:
        return "N/A"
    years = int(total_years_float)
    months = round((total_years_float - years) * 12)
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    return ", ".join(parts) if parts else "Less than a month"
