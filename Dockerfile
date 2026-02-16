FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential \
    qt5-qmake \
    make

# cannot find -lgfortran: No such file or directory
RUN apt-get install -y gfortran
# qmake: could not find a Qt installation of ''
RUN apt-get install -y qtbase5-dev qtchooser
# Project ERROR: Unknown module(s) in QT: serialport
RUN apt-get install -y qtbase5-dev libqt5serialport5-dev


############### PYTHON FOR BAYESIAN OPTIMIZATION ###############
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3-pip

# Install Pandas for GNSS-Logger parsing.
RUN pip install --no-cache-dir "pandas>=2.0,<3"

# Install tqdm to see the progress of the program execution.
RUN  pip install --no-cache-dir tqdm 

# Install tkinter for GUI matplotlib plots.
RUN apt-get update && apt-get install x11-utils python3-tk tk -y

# Install matplotlib for plotting the dataframe columns hist.
RUN pip install --no-cache-dir matplotlib scipy

RUN pip install numpy==2.0.0 simplekml
RUN pip install ipdb plotly
RUN pip install dash

RUN pip install pymap3d
RUN pip install pyproj

RUN pip install optuna
RUN pip install optuna-dashboard




COPY . /code
WORKDIR /code
RUN sed -i 's/\bNFREQ=3\b/NFREQ=4/g' RTKLib.pri
RUN sed -i 's/\bNFREQ=3\b/NFREQ=4/g' CMakeLists.txt

WORKDIR /code/app/consapp/rnx2rtkp/gcc

RUN make -j$(nproc)

WORKDIR /code/app/qtapp

RUN qmake
# /usr/bin/ld: /code/app/qtapp/../..//lib//libRTKLib.so: undefined reference to `gen_ally'
#WORKDIR /code/src
#RUN sed -i '67s|$| \n    rcv/allystar.c \\|' src.pro
WORKDIR /code/app/qtapp
RUN make -j$(nproc)
RUN ./install_qtapp


RUN pip install psycopg2-binary

CMD ["./rtkpost_qt/rtkpost_qt"]