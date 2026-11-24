CC = gcc
CFLAGS = -O2 -Wall
LIBS = -lws2_32 -lwinhttp

TARGET = server.exe
SRCS = server.c gemini.c db.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET) $(LIBS)

clean:
	del /Q $(TARGET) *.o *.obj 2>nul || rm -f $(TARGET) *.o *.obj
