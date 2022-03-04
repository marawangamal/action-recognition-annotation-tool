import os
import sys
import pandas as pd
import os.path as osp
import cv2
import numpy as np

import PyQt5
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon, QFont, QPalette, QPainter, QPixmap, QPen
from PyQt5.QtCore import QDir, Qt, QUrl, QSize
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QMainWindow, QApplication, QFileDialog, QHBoxLayout, QLabel, QSplitter,
                             QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout, QWidget, QComboBox, QListWidget,
                             QGraphicsScene, QGraphicsView, QGridLayout, QStatusBar)


class ActionAnnotator(QWidget):
    """Action recognition annotation gui for multi-person action recognition.

    Assumes tracking information is available. Finite state machine is divided into four panes:
        1. Video file navigation pane
            - Loads/Displays input video file (.mp4), and corresponding tracking file
        2. Annotations input pane
            - Controls for creating a new annotation
        3. Annotations display pane
            - Displays existent annotations
        4. Video player pane
            - Video playback

    Usage
        - Load root directory containing ``videos_tracked`` and ``annotations`` folders.
        - The ``videos_tracked`` folder must contain a list of folders, each containing a video file and a tracking file
        - Tracking file columns must be in this order: player_id, x1 (top left), y1 (top left), width, height
        - Annotations will be logged to the ``annotations`` folder under these headings:
            'vidname', 'action', 'player_id', 'start_time_s', 'stop_time_s', 'start_frame', 'stop_frame',
            'frame_coords', 'x_raw', 'y_raw'

    """

    def __init__(self, classes_list, parent=None):
        super(ActionAnnotator, self).__init__(parent)

        self.classes_list = classes_list

        # Default appearance attributes
        self.button_size = QSize(16, 16)
        self.title_font = QFont('Arial', 14, QFont.Bold)
        self.subtitle_font = QFont('Arial', 10)
        self.subtitle_font.setItalic(True)
        self.playback_elapsed_string_format = '{} / {}  ||  {} / {}'

        # Initialize video attributes
        self.fps = None
        self.current_video_name = None
        self.current_video_path = None
        self.root_dir = None  # path to data/ directory
        self.videos_tracked_dir = None
        self.annotations_dir = None
        self.videos_list = None
        self.num_frames = None
        self.vid_height = None
        self.vid_width = None
        self.tracking_annotations = None  # df containing tracking annotations
        self.mouse_x = 0
        self.mouse_y = 0
        self.frame_geometry = None

        # 1. *** Video file navigation pane ***
        self.vid_index = 0
        self.annotations_index = 0

        # Title
        self.videos_title = QLabel('Videos List')
        # self.videos_description = QLabel('Select root directory containing "videos_tracked/" and "annoations/" folders')
        self.videos_title.setFont(self.title_font)
        self.videos_qlist = QListWidget()
        self.videos_qlist.currentRowChanged.connect(self.set_video)

        # Navigation buttons
        self.nav_next_btn = QPushButton('>')
        self.nav_prev_btn = QPushButton('<')
        self.nav_prev_btn.setEnabled(False)
        self.nav_next_btn.setEnabled(False)
        self.nav_next_btn.clicked.connect(self.nav_next)
        self.nav_prev_btn.clicked.connect(self.nav_prev)

        # Load directory button
        self.nav_openButton = QPushButton()
        self.nav_openButton.setIconSize(self.button_size)
        self.nav_openButton.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.nav_openButton.clicked.connect(self.set_dirs)

        nav_layout = QVBoxLayout()
        nav_btn_layout = QHBoxLayout()

        nav_btn_layout.addWidget(self.nav_openButton)
        nav_btn_layout.addWidget(self.nav_prev_btn)
        nav_btn_layout.addWidget(self.nav_next_btn)

        nav_layout.addWidget(self.videos_title)
        # nav_layout.addWidget(self.videos_description)
        nav_layout.addLayout(nav_btn_layout)
        nav_layout.addWidget(self.videos_qlist)

        # *** 2. Annotations input pane ***
        self.input_title = QLabel('New Annotation')
        self.input_title.setFont(self.title_font)
        self.classes_label = QLabel('Class:')

        # list select input
        self.classes_qlist = QListWidget()
        self.classes_qlist.addItems(classes_list)
        self.classes_qlist.setCurrentRow(0)

        l1 = QHBoxLayout()  # sub-layout
        l1.addWidget(self.classes_qlist)

        self.start_time_label = QLabel('Start:')
        self.stop_time_label = QLabel('Stop:')
        self.player_id_label = QLabel('Player id:')

        self.start_time = QLabel('XX:XX')
        self.stop_time = QLabel('XX:XX')
        self.start_frame = QLabel('XX')
        self.stop_frame = QLabel('XX')
        self.player_id = QLabel('XX')

        self.start_time_btn = QPushButton('set')
        self.stop_time_btn = QPushButton('set')
        self.annotations_add_btn = QPushButton('add')
        self.annotations_reset_btn = QPushButton('reset')

        self.start_time_btn.setEnabled(False)
        self.stop_time_btn.setEnabled(False)
        self.annotations_add_btn.setEnabled(False)
        self.annotations_reset_btn.setEnabled(False)

        self.start_time_btn.clicked.connect(self.set_start_time)
        self.stop_time_btn.clicked.connect(self.set_stop_time)
        self.annotations_add_btn.clicked.connect(self.add_annotation)
        self.annotations_reset_btn.clicked.connect(self.reset_input)

        l2 = QHBoxLayout()
        l2.addWidget(self.start_time_label)
        l2.addWidget(self.start_time)
        l2.addWidget(self.start_frame)
        l2.addWidget(self.start_time_btn)

        l3 = QHBoxLayout()
        l3.addWidget(self.stop_time_label)
        l3.addWidget(self.stop_time)
        l3.addWidget(self.stop_frame)
        l3.addWidget(self.stop_time_btn)

        l4 = QHBoxLayout()
        l4.addWidget(self.player_id_label)
        l4.addWidget(self.player_id)

        l5 = QHBoxLayout()
        l5.addWidget(self.annotations_reset_btn)
        l5.addWidget(self.annotations_add_btn)

        input_layout = QVBoxLayout()
        input_layout.addWidget(self.input_title)

        input_layout.addWidget(self.classes_label)
        input_layout.addLayout(l1)
        input_layout.addLayout(l2)
        input_layout.addLayout(l3)
        input_layout.addLayout(l4)
        input_layout.addLayout(l5)
        input_layout.addStretch(10)

        # *** 3. Annotations display pane ***
        self.annotations_title = QLabel('Annotations')
        self.annotations_title.setFont(self.title_font)
        self.annotations_subtitle = QLabel('action, player_id, start_time (s), stop_time (s), start_frame, stop_frame')
        self.annotations_subtitle.setFont(self.subtitle_font)

        self.annotations_qlist = QListWidget()
        self.annotations_qlist.itemClicked.connect(self.seek_video_to_annotation)

        self.delete_annotation_btn = QPushButton('delete')
        self.delete_annotation_btn.setEnabled(False)
        self.delete_annotation_btn.clicked.connect(self.delete_annotation)

        annotations_layout = QVBoxLayout()
        annotations_layout.addWidget(self.annotations_title)
        annotations_layout.addWidget(self.annotations_subtitle)
        annotations_layout.addWidget(self.annotations_qlist)
        annotations_layout.addWidget(self.delete_annotation_btn)

        annotations_pane_layout = QVBoxLayout()
        annotations_pane_layout.addLayout(input_layout, 0)
        annotations_pane_layout.addLayout(annotations_layout, 5)

        # 4. *** Video player pane ***
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget(aspectRatioMode=1)

        self.time_elapsed = QLabel('{:02d}:{:02d} / {:02d}:{:02d}  ||  {}  /  {}'.format(0, 0, 0, 0, 0, 0))

        self.play_button = QPushButton()
        self.play_button.setEnabled(False)
        self.play_button.setFixedHeight(24)
        self.play_button.setIconSize(self.button_size)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play)

        # Frame control
        self.playbackspeed_forward_btn = QPushButton('>')
        self.playbackspeed_backward_btn = QPushButton('<')
        self.playbackspeed_forward_5x_btn = QPushButton('>>')
        self.playbackspeed_backward_5x_btn = QPushButton('<<')
        self.playbackspeed_forward_btn.setEnabled(False)
        self.playbackspeed_backward_btn.setEnabled(False)
        self.playbackspeed_forward_5x_btn.setEnabled(False)
        self.playbackspeed_backward_5x_btn.setEnabled(False)

        self.playbackspeed_forward_btn.clicked.connect(self.next_frame)
        self.playbackspeed_backward_btn.clicked.connect(self.prev_frame)
        self.playbackspeed_forward_5x_btn.clicked.connect(self.nnext_frame)
        self.playbackspeed_backward_5x_btn.clicked.connect(self.pprev_frame)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)

        self.status_bar = QStatusBar()
        self.status_bar.setFont(self.subtitle_font)
        self.status_bar.setFixedHeight(14)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.time_elapsed)
        control_layout.addWidget(self.position_slider)

        playback_layout = QHBoxLayout()
        playback_layout.addWidget(self.playbackspeed_backward_5x_btn)
        playback_layout.addWidget(self.playbackspeed_backward_btn)
        playback_layout.addWidget(self.playbackspeed_forward_btn)
        playback_layout.addWidget(self.playbackspeed_forward_5x_btn)

        control_and_playback_layout = QVBoxLayout()
        control_and_playback_layout.addLayout(playback_layout)
        control_and_playback_layout.addLayout(control_layout)

        video_layout = QVBoxLayout()
        video_layout.addWidget(self.video_widget)
        video_layout.addLayout(control_and_playback_layout)
        video_layout.addWidget(self.status_bar)

        # Global Layout
        global_layout = QHBoxLayout()
        global_layout.addLayout(nav_layout)
        global_layout.addLayout(annotations_pane_layout)
        global_layout.addLayout(video_layout, 10)  # 10x stretch factor

        self.setLayout(global_layout)
        self.init_media_player()

    def mousePressEvent(self, QMouseEvent):
        """ Callback that sets `player_id` when a video is playing and click is within video player """

        if not (self.media_player.isVideoAvailable()):
            return

        self.mouse_x, self.mouse_y = QMouseEvent.x(), QMouseEvent.y()
        self.frame_geometry = self.video_widget.frameGeometry().getCoords()  # [x1, y1, x2, y2]

        # check if click is within video
        if (self.frame_geometry[0] < self.mouse_x < self.frame_geometry[2] and
                self.frame_geometry[1] < self.mouse_y < self.frame_geometry[2]):
            # turn on reset
            self.annotations_reset_btn.setEnabled(True)

            # change to frame coordinates [0,1]
            x = (self.mouse_x - self.frame_geometry[0]) / (self.frame_geometry[2] - self.frame_geometry[0])
            y = (self.mouse_y - self.frame_geometry[1]) / (self.frame_geometry[3] - self.frame_geometry[1])

            player_id = self.get_player_id((x, y))
            self.player_id.setText("{}".format(player_id))
            self.update_add_btn_status()

    def keyPressEvent(self, key_id):
        """ Callback controlling video playback """
        if key_id.key() == Qt.Key_Right:
            self.media_player.setPosition(self.media_player.position() + 500)

        elif key_id.key() == Qt.Key_Left:
            self.media_player.setPosition(self.media_player.position() - 500)

        elif key_id.key() == Qt.Key_Enter or key_id.key() == Qt.Key_Return or key_id.key() == Qt.Key_Space:
            self.play()

    def set_position(self, position):
        """ Sets video playback position """
        self.media_player.setPosition(position)

    def handle_error(self):
        """ Prints error to status bar at bottom of gui """
        self.play_button.setEnabled(False)
        self.status_bar.showMessage("Error: " + self.media_player.errorString())

    def init_media_player(self):
        """ Initializes media player widget """
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.error.connect(self.handle_error)
        self.status_bar.showMessage("Ready")

    def update_add_btn_status(self):
        """ Activates/Deactivates add button"""

        if (self.start_time.text() <= self.stop_time.text() != "XX:XX" and self.start_time.text() != "XX:XX"
                and self.player_id.text() != 'XX'):
            self.annotations_add_btn.setEnabled(True)
        else:
            self.annotations_add_btn.setEnabled(False)

    def get_player_id(self, coords):
        """ Gets player tracking id from corresponding tracking .txt file """
        x, y = coords  # ints

        curr_frame = self.get_frame_number(self.media_player.position(), self.fps)
        for row in self.tracking_annotations:
            frame_num, player_id, x1, y1, w, h = row[:6]  # int, int, floats

            if int(frame_num) == curr_frame:
                point_coords = [x, y]
                box_coords = np.array([x1, y1, x1 + w, y1 + h]) / np.array(
                    [self.vid_width, self.vid_height, self.vid_width, self.vid_height])

                if box_coords[0] < point_coords[0] < box_coords[2] and box_coords[1] < point_coords[1] < box_coords[3]:
                    # print("frame_num, player_id, box_coords, point_coords")
                    # print(frame_num, player_id, box_coords, point_coords)
                    return int(player_id)

        return -1

    def reset_input(self):
        """ Reset annotations pane after an annotation is added """
        self.start_time.setText('XX:XX')
        self.stop_time.setText('XX:XX')
        self.start_frame.setText('XX')
        self.stop_frame.setText('XX')
        self.player_id.setText('XX')
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(False)

    def nav_next(self):
        """ Callback for next video file navigation button """
        self.videos_qlist.setCurrentRow(self.videos_qlist.currentRow() + 1)
        self.set_video()

    def nav_prev(self):
        """ Callback for previous video file navigation button """
        self.videos_qlist.setCurrentRow(self.videos_qlist.currentRow() - 1)
        self.set_video()

    def update_nav_clickers(self):
        """ Controls navigation button activation status """
        if self.videos_qlist.currentRow() == 0:
            self.nav_prev_btn.setEnabled(False)
        else:
            self.nav_prev_btn.setEnabled(True)

        if self.videos_qlist.currentRow() == self.videos_qlist.count() - 1:
            self.nav_next_btn.setEnabled(False)
        else:
            self.nav_next_btn.setEnabled(True)

    def set_start_time(self):
        """ Sets start time of action being annotated """
        pos = self.media_player.position()  # milliseconds
        self.start_time.setText(self.get_time_string(pos))
        self.start_frame.setText(str(self.get_frame_number(self.media_player.position(), self.fps)))
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(True)

    def set_stop_time(self):
        """ Sets stop time of action being annotated """
        pos = self.media_player.position()  # milliseconds
        self.stop_time.setText(self.get_time_string(pos))
        self.stop_frame.setText(str(self.get_frame_number(self.media_player.position(), self.fps)))
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(True)

    def set_dirs(self):
        """ Sets `videos_tracked` and `annotation` directories """

        # open select folder dialog
        self.videos_qlist.clear()
        self.annotations_qlist.clear()
        self.media_player.stop()

        # turn off nav clickers
        self.nav_prev_btn.setEnabled(False)
        self.nav_next_btn.setEnabled(False)

        # load from user selection
        self.root_dir = QFileDialog.getExistingDirectory(
            self, 'Select root directory containing videos/ and annoations/')
        self.videos_tracked_dir = osp.join(self.root_dir, 'videos_tracked')
        self.annotations_dir = osp.join(self.root_dir, 'annotations')

        if not (osp.exists(self.videos_tracked_dir) and osp.exists(self.annotations_dir)):
            self.status_bar.showMessage("ERROR: invalid directory chosen")
        else:
            # select first video and annotation
            self.videos_list = os.listdir(self.videos_tracked_dir)
            self.videos_list = [item for item in self.videos_list if '.' not in item]

            self.videos_qlist.addItems(self.videos_list)
            self.videos_qlist.setCurrentRow(0)

            self.set_video()
            self.update_nav_clickers()

            self.start_time_btn.setEnabled(True)
            self.stop_time_btn.setEnabled(True)
            self.delete_annotation_btn.setEnabled(True)

    def set_video(self):
        """Updates variables when new video is selected. Also updates and displays and its corresponding annot file"""

        # update video
        self.current_video_name = self.videos_list[self.videos_qlist.currentRow()] + '.mp4'
        self.current_video_path = osp.join(
            self.videos_tracked_dir, self.current_video_name.split('.')[0], self.current_video_name)
        cap_vid_tracked = cv2.VideoCapture(self.current_video_path)
        self.fps = cap_vid_tracked.get(cv2.CAP_PROP_FPS)
        self.num_frames = int(cap_vid_tracked.get(cv2.CAP_PROP_FRAME_COUNT))
        self.vid_height = cap_vid_tracked.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.vid_width = cap_vid_tracked.get(cv2.CAP_PROP_FRAME_WIDTH)

        # read tracking data for this video (for efficiency change to json/dict)
        tracking_results_txt_path = osp.join(self.videos_tracked_dir, self.current_video_name.split('.')[0],
                                             self.current_video_name.split('.')[0] + '.txt')
        df = pd.read_csv(tracking_results_txt_path)
        self.tracking_annotations = pd.Series.to_list(df)

        # Load annotations file if they already exist
        self.annotations_qlist.clear()
        if osp.exists(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + '.csv')):
            df = pd.read_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + '.csv'))
            self.annotations_list = pd.Series.to_list(df)
            annotation_strings = [' '.join([str(elem) + ", " for elem in row[1:-3]])[:-2]
                                  for row in self.annotations_list]
            self.annotations_qlist.addItems(annotation_strings)
            self.annotations_qlist.setCurrentRow(0)
            self.annotations_col_names = df.columns

        else:
            self.annotations_col_names = ['vidname', 'action', 'player_id', 'start_time_s', 'stop_time_s',
                                          'start_frame', 'stop_frame', 'frame_coords', 'x_raw', 'y_raw']
            self.annotations_list = []

        self.media_player.setMedia(
            QMediaContent(QUrl.fromLocalFile(self.current_video_path)))
        self.play_button.setEnabled(True)
        self.status_bar.showMessage(osp.join(self.current_video_path))
        self.update_nav_clickers()
        self.playbackspeed_forward_btn.setEnabled(True)
        self.playbackspeed_backward_btn.setEnabled(True)
        self.playbackspeed_forward_5x_btn.setEnabled(True)
        self.playbackspeed_backward_5x_btn.setEnabled(True)
        self.play()

    def add_annotation(self):
        """ Adds new annotation to list and saves to disk """

        # log to csv
        start_t = self.get_time_seconds(self.start_time.text())  # seconds
        stop_t = self.get_time_seconds(self.stop_time.text())
        player_id = int(self.player_id.text())
        vidname = self.current_video_name
        frame_coords = self.frame_geometry
        action = self.classes_list[self.classes_qlist.currentRow()]
        self.annotations_list.append(
            [vidname, action, player_id, start_t, stop_t, self.start_frame.text(), self.stop_frame.text(),
             frame_coords, self.mouse_x, self.mouse_y])

        # save to disk
        df = pd.DataFrame(self.annotations_list, columns=self.annotations_col_names)
        df.to_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + ".csv"), index=False)

        # display
        annot_str = ' '.join([str(elem) + ", " for elem in [action, player_id, start_t, stop_t]])
        self.annotations_qlist.addItem(annot_str[:-2])
        self.annotations_qlist.setCurrentRow(self.annotations_qlist.count() - 1)

        self.reset_input()

    def delete_annotation(self):
        """ Deletes an annotation and saves to disk """

        # remove annotation
        index = self.annotations_qlist.currentRow()
        self.annotations_qlist.takeItem(index)
        self.annotations_list.pop(index)

        # save to disk
        df = pd.DataFrame(self.annotations_list, columns=self.annotations_col_names)
        df.to_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + ".csv"), index=False)

    def seek_video_to_annotation(self):
        """ Seeks video to selected annotation """
        idx = self.annotations_qlist.currentRow()
        vidname, action, player_id, start_t, stop_t, start_f, stop_f, frame_coords, _, _ = self.annotations_list[idx]
        self.set_position(start_t * 1000)  # converting to ms

    def next_frame(self):
        """ Callback for next frame button """
        # curr_frame = int((self.mediaPlayer.position()/1000)*self.fps) #  miliseconds -> seconds -> frame
        next_pos = self.media_player.position() + (1 / self.fps) * 1000
        self.media_player.setPosition(next_pos)

    def nnext_frame(self):
        """ Callback for seek 5 frames button """
        # curr_frame = int((self.mediaPlayer.position()/1000)*self.fps) #  miliseconds -> seconds -> frame
        next_pos = self.media_player.position() + (5 / self.fps) * 1000
        self.media_player.setPosition(next_pos)

    def prev_frame(self):
        """ Callback for previous frame button """
        prev_pos = self.media_player.position() - (1 / self.fps) * 1000
        self.media_player.setPosition(prev_pos)

    def pprev_frame(self):
        """ Callback for seek to 5 previous frames button """
        prev_pos = self.media_player.position() - (5 / self.fps) * 1000
        self.media_player.setPosition(prev_pos)

    def play(self):
        """ Toggles video playback """
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def media_state_changed(self):
        """ Toggles appearance of play/pause button"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def position_changed(self, position):
        """ Updates playback time and frame number information """
        self.position_slider.setValue(position)
        duration = self.get_time_string(self.media_player.duration())
        curr = self.get_time_string(self.media_player.position())
        frame_num = int(self.fps * self.media_player.position() / 1000)
        self.time_elapsed.setText(
            self.playback_elapsed_string_format.format(curr, duration, frame_num, self.num_frames))

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        duration = self.get_time_string(self.media_player.duration())
        curr = self.get_time_string(self.media_player.position())
        frame_num = int(self.fps * self.media_player.position() / 1000)
        # self.time_elapsed.setText('{} / {}'.format(curr, duration))
        self.time_elapsed.setText(
            self.playback_elapsed_string_format.format(curr, duration, frame_num, self.num_frames))

    @staticmethod
    def get_time_string(time_ms):
        """ converts `time_ms` (int) to mm:ss (string) format """
        # minutes:seconds
        time_seconds = int(time_ms / 1000)
        mins = int(time_seconds / 60)
        secs = time_seconds - mins * 60

        return "{:02d}:{:02d}".format(mins, secs)

    @staticmethod
    def get_time_seconds(time_string):
        """ converts "{:02d}:{:02d}" (string) to time in seconds (int) """
        time_lst = [int(x) for x in time_string.split(":")]
        bases = [60, 1]
        return sum([time_lst[i] * bases[i] for i in range(len(time_lst))])

    @staticmethod
    def get_frame_number(position_milliseconds, fps):
        frame_number = int((position_milliseconds / 1000) * fps)
        return frame_number


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Action classes
    classes_list = ['shot', 'pass', 'advance', 'faceoff', 'forwards', 'backwards']

    main_window = QMainWindow()

    annotator_widget = ActionAnnotator(classes_list)
    annotator_widget.setWindowTitle("Action Annotation")
    annotator_widget.setWindowIcon(QtGui.QIcon('icon.png'))

    # Get screen geometry
    screen = app.primaryScreen()
    size = screen.size()
    width, height = size.width(), size.height()

    # Set gui size
    main_window.setCentralWidget(annotator_widget)
    main_window.resize(width, height)  # 1200, 500
    main_window.show()

    sys.exit(app.exec_())
