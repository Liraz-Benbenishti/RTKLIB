docker build -t rtklib_demo5_img .

docker rm -f RTKLIB-linux_2 || true


xhost +local:docker
docker run -it --name RTKLIB-linux_2 -e DISPLAY=$DISPLAY -v ~/Downloads/app:/app \
     --network optuna-net \
    -v "$(pwd)":/code2 \
    -v /tmp/.X11-unix:/tmp/.X11-unix rtklib_demo5_img \
    bash

docker exec RTKLIB-linux_2 sh -c "python3 /code2/load_parameters_to_config.py"