"""Static gate replies. These never call an LLM and never include links or join prompts."""

NON_MEMBER = "CookToFit is invite-only right now. Reply WAITLIST to be notified when we open."
WAITLIST_JOINED = (
    "Thanks, you're on the waitlist. We'll message you once when we open. Reply STOP to be removed."
)
WAITLIST_REMOVED = "Done, you've been removed from the waitlist."
CODE_NEEDED = (
    "Welcome! Please send the invite code from your invitation (it looks like CTF-XXXXXXXXXX)."
)
CODE_WRONG = "That code didn't match your invite. Please check it and try again."
INVITE_EXPIRED = "This invite has expired or been locked. Please ask for a new one."
CAPACITY_FULL = "CookToFit is at capacity right now. We've let the admin know."
CAPPED = "You've reached today's message limit. See you tomorrow!"
PAUSED = "CookToFit is paused for a short while. We'll be back soon."


def activated(name: str) -> str:
    return f"Welcome to CookToFit, {name}! Every meal is a rep. 🍳"
