"""Quest card component for displaying gamified missions and progress.

Renders quest information, target progress, dynamic progress bar, and XP reward.
"""

from typing import Any

import streamlit as st


def render_quest_card(quest: dict[str, Any]) -> None:
    """Render a gamified quest card in Letterboxd dark style.

    :param quest: Quest dictionary returned by /api/users/me/quests
    """
    title = quest.get("title", "")
    description = quest.get("description", "")
    category = quest.get("category", "READING")
    current = quest.get("current", 0)
    target = quest.get("target", 1)
    percentage = quest.get("progress_percentage", 0.0)
    is_completed = quest.get("is_completed", False)
    reward_xp = quest.get("reward_xp", 0)

    completed_class = "completed" if is_completed else ""
    status_label = "Accomplie ✨" if is_completed else f"{current} / {target}"

    card_html = f"""
    <div class="quest-card {completed_class}">
        <div class="quest-header">
            <div>
                <span class="badge-status badge-reading" style="margin-bottom: 4px;">{category}</span>
                <div class="quest-title">{title}</div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span class="badge-xp">+{reward_xp} XP</span>
            </div>
        </div>
        <div class="quest-desc">{description}</div>
        <div class="quest-progress-bg">
            <div class="quest-progress-bar" style="width: {percentage}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #8fa0b0; margin-top: 2px;">
            <span>Progression : {percentage}%</span>
            <span style="font-weight: 600; color: {"#e5a93c" if is_completed else "#8fa0b0"};">{status_label}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
