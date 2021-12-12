# action-recognition-annotation-tool

This repo contains source code for a multi-person action recognition annotation tool, typical usage is action recognition in sports videos. Video files and tracking information is required.

## Usage

 
**Select data directory**

* Select data directory by clicking on (1). 
* Data directory must contain a `videos_tracked` and an `annotations` folder
* The `videos_tracked` folder contains sub-folders, one for each video to be annotated. In these subfolders there must exist an *mp4* video file and a *txt* file containing tracking information (i.e. bounding boxes and tracking ids)


**Annotate**

1. Select class list in (2).
2. Seek to start time of the action and click on set button (3) (do the same for stop time button (4)).
3. Click on the player performing the action in the start frame (5) (ensure player id matches the bbox you clicked on).
4. Click the add button (4) to save the annotation.
5. Exit at anytime, your work is saved every time you add a new annotation.

<table style="width:85%">
  <tr>
  <img src="https://github.com/marawangamal/action-recognition-annotation-tool/blob/main/docs/labelled_img.png?raw=true" alt="Paris" class="center">
  </tr>
</table>
