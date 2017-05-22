"""
Copyright (c) 2017, Adi Roiban

MIT License
"""
import supybot.conf as conf
import supybot.registry as registry


def configure(advanced):
    conf.registerPlugin('SupportNotifications', True)


SupportNotifications = conf.registerPlugin('SupportNotifications')

conf.registerGlobalValue(
    SupportNotifications,
    'pollInterval',
    registry.Integer(10, 'Number of seconds to do the check.'),
    )

conf.registerGlobalValue(
    SupportNotifications,
    'targetChannel',
    registry.String('', 'Name of the channel where to send notifications.'),
    )

conf.registerGlobalValue(
    SupportNotifications,
    'teamDomain',
    registry.String('', 'Domain from which team members have addresses.'),
    )

conf.registerGlobalValue(
    SupportNotifications,
    'targetAddress',
    registry.String('', 'Address where support emails are sent.'),
    )

conf.registerGlobalValue(
    SupportNotifications,
    'credentialsPath',
    registry.String('path/not/defined', 'Path to Google API credentials.'),
    )

conf.registerGlobalValue(
    SupportNotifications,
    'historyID',
    registry.Integer(0, 'Last checked history ID'),
    )
