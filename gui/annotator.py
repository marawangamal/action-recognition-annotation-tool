from PyQt5.QtGui import QIcon, QFont, QPalette, QPainter, QPixmap, QPen
from PyQt5.QtCore import QDir, Qt, QUrl, QSize
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy, QSlider, QStyle, QVBoxLayout,QWidget, QComboBox, QListWidget, QGraphicsScene, QGraphicsView, QGridLayout, QStatusBar)

import os
import pandas as pd
import os.path as osp
import cv2
import numpy as np

TITLE_FONT = QFont('Arial', 14, QFont.Bold)
SUBTITLE_FONT = QFont('Arial', 10)
SUBTITLE_FONT.setItalic(True)

class ActionAnnotator(QWidget):

    def __init__(self, classes_list, parent=None):
        super(ActionAnnotator, self).__init__(parent)

        btnSize = QSize(16, 16)


        ########### Annotation Inputs

        # title
        self.input_title = QLabel('New Annotation')
        self.input_title.setFont(TITLE_FONT)


        self.classes_label = QLabel('Class:')

        # # dropdown input
        # self.classes = QComboBox()
        # self.classes.addItems(classes_list)

        # list select input
        self.classes_qlist = QListWidget()
        self.classes_list = classes_list
        self.classes_qlist.addItems(classes_list)
        self.classes_qlist.setCurrentRow(0)

        l1 = QHBoxLayout()
        # l1.addWidget(self.classes_label)
        l1.addWidget(self.classes_qlist)


        self.start_time_label = QLabel('Start:')
        self.stop_time_label = QLabel('Stop:')
        self.player_id_label = QLabel('Player id:')


        self.start_time = QLabel('XX:XX')
        self.stop_time = QLabel('XX:XX')
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
        l2.addWidget(self.start_time_btn)

        l3 = QHBoxLayout()
        l3.addWidget(self.stop_time_label)
        l3.addWidget(self.stop_time)
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



        ########### Navigation Pane
        self.vid_index = 0
        self.annotations_index = 0

        # title
        self.videos_title = QLabel('Videos List')
        self.videos_title.setFont(TITLE_FONT)
        self.videos_qlist = QListWidget()
        self.videos_qlist.currentRowChanged.connect(self.set_video)


        # buttons
        self.nav_next_btn = QPushButton('>')
        self.nav_prev_btn = QPushButton('<')
        self.nav_prev_btn.setEnabled(False)
        self.nav_next_btn.setEnabled(False)
        self.nav_next_btn.clicked.connect(self.nav_next)
        self.nav_prev_btn.clicked.connect(self.nav_prev)

        self.nav_openButton = QPushButton()
        # self.nav_openButton.setFixedHeight(16)
        self.nav_openButton.setIconSize(QSize(16, 16))
        self.nav_openButton.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.nav_openButton.clicked.connect(self.set_dirs)


        nav_layout = QVBoxLayout()
        nav_btn_layout = QHBoxLayout()

        nav_btn_layout.addWidget(self.nav_openButton)
        nav_btn_layout.addWidget(self.nav_prev_btn)
        nav_btn_layout.addWidget(self.nav_next_btn)

        nav_layout.addWidget(self.videos_title)
        nav_layout.addLayout(nav_btn_layout)
        nav_layout.addWidget(self.videos_qlist)


        ########### Annotations Pane
        self.annotations_title = QLabel('Annotations')
        self.annotations_title.setFont(TITLE_FONT)
        self.annotations_subtitle = QLabel('action, player_id, start_time, stop_time')
        self.annotations_subtitle.setFont(SUBTITLE_FONT)


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

        # nav_layout.addWidget(self.annotations_title)
        # nav_layout.addWidget(self.annotations_qlist)
        # nav_layout.addWidget(self.delete_annotation_btn)


        ############ VideoPlayer
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = QVideoWidget(aspectRatioMode=1)

        self.time_elapsed = QLabel('{:02d}:{:02d} / {:02d}:{:02d}  ||  {}  /  {}'.format(0,0,0,0, 0,0))

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setFixedHeight(24)
        self.playButton.setIconSize(btnSize)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        # frame control
        self.playbackspeed_forward_btn = QPushButton('>');  
        self.playbackspeed_backward_btn = QPushButton('<')
        self.playbackspeed_forward_btn.setEnabled(False)
        self.playbackspeed_backward_btn.setEnabled(False)

        self.playbackspeed_forward_btn.clicked.connect(self.next_frame)
        self.playbackspeed_backward_btn.clicked.connect(self.prev_frame)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.statusBar = QStatusBar()
        # self.statusBar.setFont(QFont("Noto Sans", 10))
        self.statusBar.setFont(QFont("Arial", 10))
        self.statusBar.setFixedHeight(14)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        # controlLayout.addWidget(openButton)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.time_elapsed)
        controlLayout.addWidget(self.positionSlider)
        
        playbackLayout = QHBoxLayout()
        playbackLayout.addWidget(self.playbackspeed_backward_btn)
        playbackLayout.addWidget(self.playbackspeed_forward_btn)
        # playbackLayout.addWidget(self.frames_elapsed)
    

        controlAndPlaybackLayout = QVBoxLayout()
        controlAndPlaybackLayout.addLayout(playbackLayout)
        controlAndPlaybackLayout.addLayout(controlLayout)

        video_layout = QVBoxLayout()
        video_layout.addWidget(self.videoWidget)
        video_layout.addLayout(controlAndPlaybackLayout)
        video_layout.addWidget(self.statusBar)

        #### Global Layout

        annotations_pane_layout = QVBoxLayout()
        annotations_pane_layout.addLayout(input_layout, 0)
        annotations_pane_layout.addLayout(annotations_layout, 5)

        global_layout = QHBoxLayout()
        global_layout.addLayout(nav_layout)
        global_layout.addLayout(annotations_pane_layout)
        global_layout.addLayout(video_layout, 10) # 5x stretch factor


        self.setLayout(global_layout)
        self.init_media_player()



    def init_media_player(self):
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)
        self.statusBar.showMessage("Ready")

    def mousePressEvent(self, QMouseEvent):
        if not (self.mediaPlayer.isVideoAvailable()):
            return
        self.x, self.y = QMouseEvent.x(), QMouseEvent.y()
        self.frame_geometry = self.videoWidget.frameGeometry().getCoords() #[x1, y1, x2, y2]


        # check if click is within video
        if(self.frame_geometry[0] < self.x < self.frame_geometry[2] and self.frame_geometry[1] < self.y  < self.frame_geometry[2]):

            # turn on reset
            self.annotations_reset_btn.setEnabled(True)

            # change to frame coordinates [0,1]
            x = (self.x - self.frame_geometry[0]) / (self.frame_geometry[2] - self.frame_geometry[0])
            y = (self.y - self.frame_geometry[1]) / (self.frame_geometry[3] - self.frame_geometry[1])


            player_id = self.get_player_id((x,y))
            self.player_id.setText("{}".format(player_id))

            # self.player_id.setText("({}, {})".format(x, y))
            print("video_geometry: ", self.frame_geometry)
            print("(x, y): ({}, {}), ".format(x, y))
            print("status: ", self.mediaPlayer.isVideoAvailable())
            print("")
            #
            self.update_add_btn_status()

    def update_add_btn_status(self):

        if (self.start_time.text() <= self.stop_time.text() and self.start_time.text() != "XX:XX"
        and self.stop_time.text() != "XX:XX"
         and self.player_id.text() != 'XX'):
            self.annotations_add_btn.setEnabled(True)
        else:
            self.annotations_add_btn.setEnabled(False)


    def get_player_id(self, coords):
        x,y = coords #ints

        curr_frame = int((self.mediaPlayer.position()/1000)*self.fps) # miliseconds
        for row in self.tracking_annotations:
            frame_num, player_id, x1, y1, w, h = row[:6] #int, int, floats

            if (int(frame_num) == curr_frame):
                point_coords = [x, y]
                box_coords = np.array([x1, y1, x1+w, y1+h]) / np.array([self.vid_width, self.vid_height, self.vid_width, self.vid_height])

                if self.isIn(point_coords, box_coords):
                    print("frame_num, player_id, box_coords, point_coords")
                    print(frame_num, player_id, box_coords, point_coords)
                    return int(player_id)

        return -1

    def isIn(self, point_coords, box_coords):
        """ checks if point (x, y) falls in box (x1, y1, x2, y2) """

        if (box_coords[0] < point_coords[0] and point_coords[0] < box_coords[2] and
            box_coords[1] < point_coords[1] and point_coords[1] < box_coords[3]):
            return True
        else:
            return False



    def reset_input(self):
        """ reset input after an annotation is added to avoid confusing events
        """
        self.start_time.setText('XX:XX')
        self.stop_time.setText('XX:XX')
        self.player_id.setText('XX')
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(False)

    def keyPressEvent(self, e):
        # print(e.key())
        if e.key() == Qt.Key_Right:
            # print("right")
            self.mediaPlayer.setPosition(self.mediaPlayer.position() + 500)

        elif e.key() == Qt.Key_Left:
            # print("left")
            self.mediaPlayer.setPosition(self.mediaPlayer.position() - 500)

        elif e.key() == Qt.Key_Enter or e.key() == Qt.Key_Return:
            self.play()

    def nav_next(self):
        self.videos_qlist.setCurrentRow(self.videos_qlist.currentRow() + 1)
        self.set_video()

    def nav_prev(self):
        self.videos_qlist.setCurrentRow(self.videos_qlist.currentRow() - 1)
        self.set_video()

    def update_nav_clickers(self):
        if(self.videos_qlist.currentRow() == 0):
            self.nav_prev_btn.setEnabled(False)
        else:
            self.nav_prev_btn.setEnabled(True)

        if(self.videos_qlist.currentRow() == self.videos_qlist.count() - 1):
            self.nav_next_btn.setEnabled(False)
        else:
            self.nav_next_btn.setEnabled(True)

    def set_start_time(self):
        pos = self.mediaPlayer.position() # miliseconds
        self.start_time.setText(self.format_video_time(pos))
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(True)

    def set_stop_time(self):
        pos = self.mediaPlayer.position() # miliseconds
        self.stop_time.setText(self.format_video_time(pos))
        self.update_add_btn_status()
        self.annotations_reset_btn.setEnabled(True)

    def format_video_time(self, time_ms):
        """ converts time_ms (int) to mm:ss (string)
        """

        # mins:secs
        time_seconds = int(time_ms/1000)
        mins = int(time_seconds / 60)
        secs = time_seconds - mins*60

        return "{:02d}:{:02d}".format(mins, secs)

    def time_string_to_int(self, time_string):
        """ converts "{:02d}:{:02d}" (string) to time in seconds (int)
        """
        time_lst = [int(x) for x in time_string.split(":")]
        bases = [60, 1]
        return sum([time_lst[i]*bases[i] for i in range(len(time_lst)) ])

    def set_dirs(self):
        """ sets video and annotation directories
        """
        # open select folder dialog
        self.videos_qlist.clear()
        self.annotations_qlist.clear()
        self.mediaPlayer.stop()

        # turn off nav clickers
        self.nav_prev_btn.setEnabled(False)
        self.nav_next_btn.setEnabled(False)


        # load from user selection
        self.root_dir = QFileDialog.getExistingDirectory(self, 'Select root directory containing videos/ and annoations/')
        self.videos_dir = osp.join(self.root_dir, 'videos')
        self.videos_tracked_dir = osp.join(self.root_dir, 'videos_tracked')
        self.annotations_dir = osp.join(self.root_dir, 'annotations')

        if(not (osp.exists(self.videos_dir) and osp.exists(self.annotations_dir))):
            self.statusBar.showMessage("ERROR: invalid directory chosen")
        else:
            # select first video and annotation
            self.videos_list = os.listdir(self.videos_tracked_dir)
            # [self.videos_list.remove(p) for p in self.videos_list if '.mp4' not in p]


            self.videos_list = [item for item in self.videos_list if '.' not in item]
            print("vids list")
            print(self.videos_list)




            self.videos_qlist.addItems(self.videos_list)
            self.videos_qlist.setCurrentRow(0)

            self.set_video()

            # video
            # self.mediaPlayer.setMedia(
            #         QMediaContent(QUrl.fromLocalFile(os.path.join(self.videos_dir, self.current_video_name))))

            # # tracked video
            # self.mediaPlayer.setMedia(
            #         QMediaContent(QUrl.fromLocalFile(os.path.join(self.videos_tracked_dir, self.current_video_name.split('.')[0], self.current_video_name))))
            # self.playButton.setEnabled(True)
            self.update_nav_clickers()

            self.start_time_btn.setEnabled(True)
            self.stop_time_btn.setEnabled(True)
            self.delete_annotation_btn.setEnabled(True)

            # self.play()

            # load annoation .csv if it exists
            if(osp.exists(osp.join(self.annotations_dir, self.current_video_name))):
                self.set_annotations()

    def set_video(self):
        """ updates variables when new video is selected. Also updates and displays and its corresponding annotation file
        """

        # update video
        self.current_video_name = self.videos_list[self.videos_qlist.currentRow()] + '.mp4'
        self.current_video_path = osp.join(self.videos_tracked_dir, self.current_video_name.split('.')[0], self.current_video_name)
        cap_vid_tracked = cv2.VideoCapture(self.current_video_path)
        self.fps = cap_vid_tracked.get(cv2.CAP_PROP_FPS)
        self.num_frames = int(cap_vid_tracked.get(cv2.CAP_PROP_FRAME_COUNT))
        self.vid_height = cap_vid_tracked.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.vid_width = cap_vid_tracked.get(cv2.CAP_PROP_FRAME_WIDTH)


        # read tracking data for this video (for efficiency change to json/dict)
        tracking_results_txt_path = osp.join(self.videos_tracked_dir, self.current_video_name.split('.')[0], self.current_video_name.split('.')[0] + '.txt')
        df = pd.read_csv(tracking_results_txt_path)
        self.tracking_annotations = pd.Series.to_list(df)

        self.annotations_qlist.clear()
        if(osp.exists(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + '.csv'))):
            df = pd.read_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + '.csv'))
            self.annotations_list = pd.Series.to_list(df)
            annot_strs = [' '.join([str(elem) + ", " for elem in row[1:-3] ])[:-2]
            for row in self.annotations_list]
            self.annotations_qlist.addItems(annot_strs)
            self.annotations_qlist.setCurrentRow(0)
            self.annotations_col_names = df.columns

        else:
            self.annotations_col_names = ['vidname', 'action', 'player_id', 'start_t', 'stop_t', 'frame_coords', 'x_raw', 'y_raw']
            self.annotations_list = []

        self.mediaPlayer.setMedia(
                QMediaContent(QUrl.fromLocalFile(self.current_video_path)))
        self.playButton.setEnabled(True)
        self.statusBar.showMessage(osp.join(self.current_video_path))
        self.update_nav_clickers()
        self.playbackspeed_forward_btn.setEnabled(True)
        self.playbackspeed_backward_btn.setEnabled(True)
        self.play()

    def add_annotation(self):
        """ adds a new annotation, and saves to disk
        """

        # log to csv
        start_t = self.time_string_to_int(self.start_time.text()) # seconds
        stop_t = self.time_string_to_int(self.stop_time.text())
        player_id = int(self.player_id.text())
        vidname = self.current_video_name
        frame_coords = self.frame_geometry
        action = self.classes_list[self.classes_qlist.currentRow()]
        self.annotations_list.append([vidname, action, player_id, start_t, stop_t, frame_coords, self.x, self.y])

        df = pd.DataFrame(self.annotations_list,  columns=self.annotations_col_names)
        df.to_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + ".csv"), index=False)

        # display
        annot_str = ' '.join([str(elem) + ", " for elem in [action, player_id, start_t, stop_t]])
        self.annotations_qlist.addItem(annot_str[:-2])
        self.annotations_qlist.setCurrentRow(self.annotations_qlist.count() - 1)

        self.reset_input()

    def delete_annotation(self):
        index = self.annotations_qlist.currentRow()
        self.annotations_qlist.takeItem(index)
        self.annotations_list.pop(index)

        df = pd.DataFrame(self.annotations_list, columns=self.annotations_col_names)
        df.to_csv(osp.join(self.annotations_dir, self.current_video_name.split('.')[0] + ".csv"), index=False)

    def seek_video_to_annotation(self):
        idx = self.annotations_qlist.currentRow()
        vidname, action, player_id, start_t, stop_t, frame_coords, _, _  = self.annotations_list[idx]
        self.setPosition(start_t*1000) # converting to ms


    def next_frame(self):
        # curr_frame = int((self.mediaPlayer.position()/1000)*self.fps) # miliseconds -> seconds -> frame
        next_pos = self.mediaPlayer.position() + (1/self.fps)*1000 
        self.mediaPlayer.setPosition(next_pos)

    def prev_frame(self):
        prev_pos = self.mediaPlayer.position() - (1/self.fps)*1000
        self.mediaPlayer.setPosition(prev_pos)

    def abrir(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Selecciona los mediose",
                ".", "Video Files (*.mp4 *.flv *.ts *.mts *.avi)")

        if fileName != '':
            self.mediaPlayer.setMedia(
                    QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.statusBar.showMessage(fileName)
            self.play()

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)
        duration = self.format_video_time(self.mediaPlayer.duration())
        curr = self.format_video_time(self.mediaPlayer.position())
        frame_num = int(self.fps* self.mediaPlayer.position()/1000)
        self.time_elapsed.setText('{}  /  {}  ||  {}  /  {}'.format(curr, duration, frame_num, self.num_frames))



    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)
        duration = self.format_video_time(self.mediaPlayer.duration())
        curr = self.format_video_time(self.mediaPlayer.position())
        frame_num = int(self.fps* self.mediaPlayer.position()/1000)
        # self.time_elapsed.setText('{} / {}'.format(curr, duration))
        self.time_elapsed.setText('{}  /  {}  ||  {}  /  {}'.format(curr, duration, frame_num, self.num_frames))


    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        self.statusBar.showMessage("Error: " + self.mediaPlayer.errorString())



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    classes_list = ['shot', 'pass', 'advance', 'faceoff', 'forwards', 'backwards']


    player = ActionAnnotator(classes_list)
    player.setWindowTitle("Action Annotation")
    player.resize(1200, 500)
    player.show()



    sys.exit(app.exec_())
