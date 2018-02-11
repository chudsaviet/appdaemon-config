import datetime

import appdaemon.plugins.hass.hassapi as hass

#
# Daily vacuuming with lights on
# Created for Appdaemon 3.x
#


class Vacuum(hass.Hass):

    def __init__(self, ad, name, logger, error, args, config, app_config, global_vars):

        super(Vacuum, self).__init__(ad, name, logger, error, args, config, app_config, global_vars)

        self.vacuum_entity = None
        self.lights = None
        self.lights_state_map = None
        self.device_trackers = None
        self.reset_time = None
        self.no_one_in_home_listener_handle = None
        self.vacuuming_finished_handle = None

    def initialize(self):
        self.vacuum_entity = "vacuum.%s" % self.args["device"]
        self.lights = self.args["lights"]
        self.device_trackers = ["device_tracker.%s" % x for x in self.args["device_trackers"]]

        start_time = datetime.datetime.strptime(self.args["vacuuming_time"], '%H:%M').time()
        self.reset_time = datetime.datetime.strptime(self.args["reset_time"], '%H:%M').time()

        self.log("Scheduling vacuuming using %s to %s" % (self.vacuum_entity, start_time))
        self.run_daily(self.schedule_vacuuming, start_time)

    def anyone_specified_home(self):
        state = self.get_state("device_tracker")
        for entity_id, state_desc in state.items():
            if entity_id in self.device_trackers:
                if state_desc["state"] == "home":
                    return True
        return False

    def start_vacuuming(self):
        self.log("Starting vacuuming using %s " % self.vacuum_entity)
        self.capture_lights_states()
        self.turn_all_lights_on()
        self.turn_on(self.vacuum_entity)
        self.vacuuming_finished_handle = self.listen_state(self.vacuuming_finished_listener, "vacuum")

    def schedule_vacuuming(self, kwargs):
        if not self.anyone_specified_home():
            self.log("No one in home")
            self.start_vacuuming()
        else:
            self.log("Someone in home, waiting until everyone will leave")
            self.no_one_in_home_listener_handle = self.listen_state(self.no_one_in_home_listener, "device_tracker")
            self.run_at(
                self.cancel_no_one_in_home_listener,
                datetime.datetime.combine(datetime.date.today(), self.reset_time)
            )

    def no_one_in_home_listener(self, entity, attribute, old, new, kwargs):
        if entity in self.device_trackers:
            if not self.anyone_specified_home():
                self.log("Everyone left")
                self.start_vacuuming()
                self.cancel_listen_state(self.no_one_in_home_listener_handle)

    def capture_lights_states(self):
        self.log("Saving states of all lights")
        self.lights_state_map = {}
        for entity in self.lights:
            self.lights_state_map[entity] = self.get_state(entity)
            self.log("%s - %s" % (entity, self.lights_state_map[entity]), "DEBUG")

    def restore_lights_states(self):
        self.log("Restoring states of all lights")
        for entity, state in self.lights_state_map.items():
            self.set_on_off_state(entity, state)
        self.lights_state_map = None

    def turn_all_lights_on(self):
        self.log("Turning all lights on")
        for entity in self.lights:
            self.turn_on(entity)

    def vacuuming_finished_listener(self, entity, attribute, old, new, kwargs):
        if entity == self.vacuum_entity and new == "off":
            self.log("Vacuuming finished")
            self.restore_lights_states()
            self.cancel_listen_state(self.vacuuming_finished_handle)

    def cancel_no_one_in_home_listener(self, kwargs):
        self.log("Reset time reached, cancelling today's vacuuming")
        self.cancel_listen_state(self.no_one_in_home_listener_handle)

    def set_on_off_state(self, entity, state):
        if state == "on":
            self.turn_on(entity)
        elif state == "off":
            self.turn_off(entity)
        else:
            raise Exception("Can only set on or off, but %s passed" % state)