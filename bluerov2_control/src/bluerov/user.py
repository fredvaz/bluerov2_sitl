#!/usr/bin/env python
"""

From bluerov_ros_playground respository (https://github.com/patrickelectric/bluerov_ros_playground)
Credits: patrickelectric

"""

import cv2
import rospy
import time

try:
    import pubs
    import subs
    import video
except:
    import bluerov.pubs as pubs
    import bluerov.subs as subs
    import bluerov.video as video

from geometry_msgs.msg import TwistStamped
from mavros_msgs.srv import CommandBool
from sensor_msgs.msg import JointState, Joy

from sensor_msgs.msg import BatteryState
from mavros_msgs.msg import OverrideRCIn, RCIn, RCOut


class Code(object):

    """Class to provide user access

    Attributes:
        cam (Video): Video object, get video stream
        pub (Pub): Pub object, do topics publication
        sub (Sub): Sub object, subscribe in topics
    """

    def __init__(self):
        super(Code, self).__init__()

        # Do what is necessary to start the process
        # and to leave gloriously
        self.arm()

        self.sub = subs.Subs()
        self.pub = pubs.Pubs()

        self.pub.subscribe_topic('/mavros/rc/override', OverrideRCIn)
        self.pub.subscribe_topic('/mavros/setpoint_velocity/cmd_vel', TwistStamped)

        # Thrusters Input
        self.pub.subscribe_topic('/bluerov2/thrusters/0/input', FloatStamped)
        self.pub.subscribe_topic('/bluerov2/thrusters/1/input', FloatStamped)
        self.pub.subscribe_topic('/bluerov2/thrusters/2/input', FloatStamped)
        self.pub.subscribe_topic('/bluerov2/thrusters/3/input', FloatStamped)
        self.pub.subscribe_topic('/bluerov2/thrusters/4/input', FloatStamped)
        self.pub.subscribe_topic('/bluerov2/thrusters/5/input', FloatStamped)


        self.sub.subscribe_topic('/joy', Joy)
        self.sub.subscribe_topic('/mavros/battery', BatteryState)
        self.sub.subscribe_topic('/mavros/rc/in', RCIn)
        self.sub.subscribe_topic('/mavros/rc/out', RCOut)

        self.cam = None
        try:
            video_udp_port = rospy.get_param("/user_node/video_udp_port")
            rospy.loginfo("video_udp_port: {}".format(video_udp_port))
            self.cam = video.Video(video_udp_port)
        except Exception as error:
            rospy.loginfo(error)
            self.cam = video.Video()


    def arm(self):
        """ Arm the vehicle and trigger the disarm
        """
        rospy.wait_for_service('/mavros/cmd/arming')

        self.arm_service = rospy.ServiceProxy('/mavros/cmd/arming', CommandBool)
        self.arm_service(True)

        # Disarm is necessary when shutting down
        rospy.on_shutdown(self.disarm)


    @staticmethod
    def pwm_to_thrust(pwm):
        """Transform pwm to thruster value is in UUV Simulator. Here we give an offset to positive and negative values.
        The equation come from:
            http://docs.bluerobotics.com/thrusters/#t100-thruster-specifications
            In our case we are using T100 Thrusters on BlueROV2
        Args:
            pwm (int): pwm value

        Returns:
            int: pwm value offsetted to positive and negative values
        """
        # PWM to Forward
        if pwm > 1500:
            pwm = pwm * gain - 1500;
        # PWM to Backward
        else:
            if pwm < 1500:
                pwm = pwm * gain - 1500;
        # PWM to STOP
        else:
            thrust = 0;
        return

    def run(self):
        """Run user code
        """
        while not rospy.is_shutdown():
            time.sleep(0.1)
            # Try to get data
            try:
                rospy.loginfo(self.sub.get_data()['mavros']['battery']['voltage'])
                rospy.loginfo(self.sub.get_data()['mavros']['rc']['in']['channels'])
                rospy.loginfo(self.sub.get_data()['mavros']['rc']['out']['channels'])
            except Exception as error:
                print('Get data error:', error)

            try:
                # Get joystick data
                joy = self.sub.get_data()['joy']['axes']

                # rc run between 1100 and 2000, a joy command is between -1.0 and 1.0
                override = [int(val*400 + 1500) for val in joy]
                for _ in range(len(override), 8):
                    override.append(0)
                # Send joystick data as rc output into rc override topic
                # (fake radio controller)
                self.pub.set_data('/mavros/rc/override', override)
            except Exception as error:
                print('joy error:', error)

            try:
                # Get pwm output and send it to Gazebo model
                rc = self.sub.get_data()['mavros']['rc']['out']['channels']

                # Variable object type of
                _input = FloatStamped();
                # Array size of rc
                _input = [self.pwm_to_thrust(pwm) for pwm in rc]

                # Send Thrusters Input FloatStamped
                self.pub.set_data('bluerov2/thrusters/0/input', _input[0])
                self.pub.set_data('bluerov2/thrusters/1/input', _input[1])
                self.pub.set_data('bluerov2/thrusters/2/input', _input[2])
                self.pub.set_data('bluerov2/thrusters/3/input', _input[3])
                self.pub.set_data('bluerov2/thrusters/4/input', _input[4])
                self.pub.set_data('bluerov2/thrusters/5/input', _input[5])

            except Exception as error:
                print('rc error:', error)

            try:
                if not self.cam.frame_available():
                    continue

                # Show video output
                frame = self.cam.frame()
                cv2.imshow('frame', frame)
                cv2.waitKey(1)
            except Exception as error:
                print('imshow error:', error)

    def disarm(self):
        self.arm_service(False)


if __name__ == "__main__":
    try:
        rospy.init_node('user_node', log_level=rospy.DEBUG)
    except rospy.ROSInterruptException as error:
        print('pubs error with ROS: ', error)
        exit(1)
    code = Code()
    code.run()
