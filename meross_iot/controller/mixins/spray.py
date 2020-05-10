import logging
from typing import Optional, Union

from meross_iot.model.enums import Namespace, LightMode, SprayMode
from meross_iot.model.plugin.light import LightInfo
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.typing import RgbTuple
from meross_iot.utilities.conversion import rgb_to_int

_LOGGER = logging.getLogger(__name__)


class SprayMixin(object):
    _execute_command: callable
    _abilities_spec: dict
    handle_update: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_spray_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.CONTROL_SPRAY:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('spray')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'spray' attribute in push notification data: "
                              f"{push_notification.raw_data}")
                locally_handled = False
            else:
                # Update the status of every channel that has been reported in this push
                # notification.
                for c in payload:
                    channel = c['channel']
                    strmode = c['mode']
                    mode = SprayMode(strmode)
                    self._channel_spray_status[channel] = mode

                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    def get_mode(self, channel: int = 0, *args, **kwargs) -> Optional[SprayMode]:
        return self._channel_spray_status.get(channel)

    def handle_update(self, data: dict) -> None:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        spray_data = data.get('all', {}).get('digest', {}).get('spray', [])
        for c in spray_data:
            channel = c['channel']
            strmode = c['mode']
            mode = SprayMode(strmode)
            self._channel_spray_status[channel] = mode
        super().handle_update(data=data)

    async def async_set_mode(self, mode: SprayMode, channel: int = 0, *args, **kwargs) -> None:
        payload = {'spray': {'channel': channel, 'mode': mode.value}}
        await self._execute_command(method='SET', namespace=Namespace.CONTROL_SPRAY, payload=payload)
        # Immediately update local state
        self._channel_spray_status[channel] = mode
