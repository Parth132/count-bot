# count-bot
Discord counting bot

## `/count-ban`

Users with one of the configured allowed roles can run `/count-ban` with a member and a duration in minutes. The ban applies only to the configured counting channel, persists across bot restarts, and affects new messages until it expires. Each attempted message is deleted and the bot posts a notice in the channel.
