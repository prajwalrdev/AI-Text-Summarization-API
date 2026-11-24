CC = gcc
CFLAGS = -O2 -Wall
LIBS = -lws2_32 -lwinhttp

# PostgreSQL integration (optional, for native libpq support)
PG_PATH = C:/Program Files/PostgreSQL/19
PG_FLAGS = -DUSE_LIBPQ -I"$(PG_PATH)/include" -L"$(PG_PATH)/lib" -llibpq

TARGET = server.exe
SRCS = server.c gemini.c db.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET) $(LIBS)

# Build with native PostgreSQL libpq integration
postgres: $(SRCS)
	$(CC) $(CFLAGS) $(PG_FLAGS) $(SRCS) -o $(TARGET) $(LIBS)

clean:
	del /Q $(TARGET) *.o *.obj 2>nul || rm -f $(TARGET) *.o *.obj
