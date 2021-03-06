
#!/usr/bin/env python

import cv2
import rospy
import numpy as np
import matplotlib.pyplot as plt
from std_msgs.msg import Float32MultiArray
from genesis_msgs.msg import target
from genesis_msgs.msg import Multi_targets

pub_acc             = rospy.Publisher('radar_targets_acc', target, queue_size=10)
pub_all_targets     = rospy.Publisher('multi_targets', Multi_targets, queue_size=10)


radar_list_targets           = None
camera_list_targets          = None

previous_camera_list_targets = None
previous_radar_list_targets  = None


def callback_radar(data):
	global radar_list_targets
	radar_list_targets = data.data



def callback_camera(data):
	global camera_list_targets
	camera_list_targets = data.data


def main():
   	global camera_list_targets, radar_list_targets, previous_camera_list_targets, previous_radar_list_targets

	rospy.init_node('listener', anonymous=True)

	rospy.Subscriber("radar_targets", Float32MultiArray, callback_radar)
	rospy.Subscriber("camera_targets", Float32MultiArray, callback_camera)


	# ------------------------------------------------------------
	# Initialize the figure
	f, ax = plt.subplots(1)
	plt.ion()

	# ------------------------------------------------------------


	while not rospy.is_shutdown():

		# Refresh plot
		ax.clear()

		# ------------------------------------------------------------
		# If no targets detected, the global variables are not updated so
                # they stay equal to they previous value. So if that happens, we set
                # them to None. Maybe better to do an empty tuple instead.

		if camera_list_targets == previous_camera_list_targets:
			camera_list_targets = None

		if radar_list_targets == previous_radar_list_targets:
			radar_list_targets = None

		# ------------------------------------------------------------
		# Reshape the lists to make it easier to work.
		# We only reshape if it's not a None, of course
		# We change the name (ex: radar_list_targets_matrix to still be able to compare with previous value at the end of the main

		radar_list_targets_matrix  = []
		camera_list_targets_matrix = []

		if radar_list_targets != None:
			radar_list_targets_matrix  = np.array(radar_list_targets).reshape(len(radar_list_targets)/4,4)     # Number of rows and columns (x,y,speed,label)

		if camera_list_targets != None:
			camera_list_targets_matrix = np.array(camera_list_targets).reshape(len(camera_list_targets)/5, 5)  # Number of rows and columns (x,y,speed)



		# ------------------------------------------------------------
		# Here we do the fusion. We go through all the points and:
		# -> Calculate the distance between all the camera points with the radar points
                #   -> If they are close, we do an average
		#   -> If not close, we keep them both
		# We append everything in a new matrix

		# LABEL: 1.0 = Car
		#        2.0 = Unknown

		all_targets = []
		min_distance = 5 #Min distance between two points to be considered the same points
		
		# Create an object of type Multi_targets() -> Will store all the detected targets (of type target)
		target_array = Multi_targets()

		for i in range(0, len(camera_list_targets_matrix)):        #camera targets loop
			print 'i = ', i

			close_points = []
			x_cam     = camera_list_targets_matrix[i][0]
			y_cam     = camera_list_targets_matrix[i][1]
			v_cam     = camera_list_targets_matrix[i][2] #Speed
			label_cam = camera_list_targets_matrix[i][3]
			age_cam   = camera_list_targets_matrix[i][4]

			close_points = np.append(close_points, [x_cam, y_cam, v_cam])
			print 'x_cam = ', x_cam
			print 'y_cam = ', y_cam
			print ' '
			
			for j in range(0, len(radar_list_targets_matrix)): #radar targets loop
				print 'j = ', j


				x_radar     = radar_list_targets_matrix[j][0]
				y_radar     = radar_list_targets_matrix[j][1]
				v_radar     = radar_list_targets_matrix[j][2]  #Speed
				label_radar = radar_list_targets_matrix[j][3]

				print 'x_radar = ', x_radar
				print 'y_radar = ', y_radar
				distance = np.sqrt( (x_radar - x_cam)**2 + (y_radar - y_cam)**2 )
				print 'distance = ', distance

				if distance < min_distance:
					print 'Fusion !'
					
					close_points = np.append(close_points, [x_radar, y_radar, v_radar])
					print 'close_points = ', close_points


				elif distance > min_distance:
					print 'No Fusion !'

					# We add the label (1.0 = car, 2.0 = unknown)
					b = np.append(radar_list_targets_matrix[j],2.0)
					
					all_targets.append(list(b))

					target_far = target()
					target_far.pos_x    = x_radar
					target_far.pos_y    = y_radar
					target_far.speed    = v_radar
					target_far.category = 2
					target_far.counter  = j

					target_array.data.append(target_far)

			matrix_close_points = np.reshape(close_points,(len(close_points)/3,3))
			x_avg = np.mean(matrix_close_points[:,0])
			y_avg = np.mean(matrix_close_points[:,1])
			v_avg = np.mean(matrix_close_points[:,2])

			# ---------------------
			# This is for publishing
			target_avg = target()
			target_avg.pos_x    = x_avg
			target_avg.pos_y    = y_avg
			target_avg.speed    = v_avg
			target_avg.category = 1
			target_avg.counter  = i   # Not relevant to put i

			# Append the avg point (the points close to car) in the target array
			target_array.data.append(target_avg)

			# ---------------------
			# This is for plotting
			# We average and add the label (1.0 = car)
			point_average = [x_avg, y_avg, v_avg, 1.0]
			all_targets.append(point_average)

			# ---------------------
			# Publish for ACC
			pub_acc.publish(target_avg)			

		pub_all_targets.publish(target_array)
		
		
		# ------------------------------------------------------------
		# Here we plot the targets
		# Change the indexes !
		#print type(all_targets)
		print all_targets
		print ' '
		#column_of_x = [i[0] for i in all_targets]
		#column_of_y = [i[1] for i in all_targets]

		#ax.scatter(column_of_x, column_of_y,color='green', marker='.')

		# ------------------------------------------------------------
		# Plot test
		for i in range(len(all_targets)):
			if all_targets[i][3] == 1.0:
				ax.scatter(all_targets[i][0], all_targets[i][1], color = 'green', marker = '.')
		 	else:
		 		ax.scatter(all_targets[i][0], all_targets[i][1], color = 'red', marker = '.')

	    # End plot test
		# ------------------------------------------------------------

		plt.xlim([-20,20])
		plt.ylim([-1,40])
		plt.grid()
		f.canvas.draw()  # Do I need this ?
		plt.pause(0.001) # Do I need this ?


		# ------------------------------------------------------------
		# Update the new previous global variables
		previous_camera_list_targets = camera_list_targets
		previous_radar_list_targets  = radar_list_targets
		# ------------------------------------------------------------

		rospy.sleep(0.5)

	rospy.spin()

if __name__ == '__main__':

	main()
