CFLAGS   = -Iinterface -Wall -Werror -g -O1 -fno-omit-frame-pointer -lmath -fpic
CXXFLAGS = $(CFLAGS) $(shell root-config --cflags) -I$(shell root-config --incdir)
LDFLAGS  = -g -I. -Iinterface $(shell root-config --cflags)
VPATH ::= ./src ./interface
LIBS ::= cConstants_c.so FakeRates_cpp.so
LIBPATHS ::= $(patsubst %,lib/%,$(LIBS))

### Main target
default: $(LIBPATHS)
.PHONY: default

### Do not try to remake sources
Makefile:;
# C headers and sources
%.h:;
%.c:;
# C++ headers and sources
%.hpp:;
%.cpp:;

### Build rules
# C object files
bin/%_c.o: src/%.c interface/%.h | bin
	$(CC) ${CFLAGS} -c $< -o $@
.NOTINTERMEDIATE: bin/cConstants_c.o

# C shared libraries are made from the corresponding object files
lib/%_c.so: bin/%_c.o | lib
	$(CC) -rdynamic -shared $< -o $@

# C++ libraries are compiled with root from the source
lib/%_cpp.so: src/%.cpp interface/%.hpp | lib
	root -l -e ".I ./interface" -e ".L $<++" -q
	mv src/$(*)_* lib/

bin lib:
	mkdir $@

### Utiltity phony targets
debug:
	@echo "LIBPATHS: $(LIBPATHS)"
.PHONY: debug

clean:
	-rm bin/* lib/*
.PHONY: clean
