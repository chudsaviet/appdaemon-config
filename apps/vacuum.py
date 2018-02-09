import time
import datetime

import appdaemon.plugins.hass.hassapi as hass

#
# Daily vacuuming with lights on
#


class Vacuum(hass.Hass):

    def __init__(self):
        self.vacuum_entity = ""
        self.lights = []
        self.device_trackers = []
        self.all_in_home_wait_handle = None

    def initialize(self):
        self.vacuum_entity = "vacuum.%s" % self.args["device"]
        self.lights = self.args["lights"]
        self.device_trackers = ["device_tracker.%s" % x for x in self.args["device_trackers"]]

        start_time = datetime.datetime.strptime(self.args["time"], '%H:%M').time()

        self.log("Scheduling vacuuming using %s to %s" % (self.vacuum_entity, start_time))
        self.run_daily(self.schedule_vacuuming, start_time)

    def anyone_specified_home(self):
        state = self.get_state("device_tracker")
        for entity_id, state_desc in state.iteritems():
            if entity_id in self.device_trackers:
                if state_desc["state"] == "home":
                    return True
        return False

    def start_vacuuming(self):
        # TODO: Turn lights on when vacuuming
        self.turn_on(self.vacuum_entity)

    def schedule_vacuuming(self, kwargs):
        if not self.anyone_specified_home():
            self.start_vacuuming()
        else:
            # TODO: Turn listener off on 12:00 AM
            self.listen_state(self.device_tracker_state_changed, "device_tracker")

    def device_tracker_state_changed(self, entity, attribute, old, new, kwargs):
        if entity in self.device_trackers:
            if not self.anyone_specified_home():
                self.start_vacuuming()
        else:
            pass
