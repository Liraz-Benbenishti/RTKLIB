docker build -t rtklib_demo5_img .

xhost +local:docker
docker run -it -e DISPLAY=$DISPLAY -v /home/liraz/Desktop/input:/input -v /tmp/.X11-unix:/tmp/.X11-unix rtklib_demo5_img bash
