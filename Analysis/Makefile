CFLAGS     ?= -Iinterface -Wall -Werror -O3 -lmath -fpic #-g -fno-omit-frame-pointer
CXXFLAGS   ?= $(CFLAGS) $(shell root-config --cflags) -I$(shell root-config --incdir) -I$(CMSSW_BASE)/src/JHUGenMELA/MELA/interface
LDFLAGS    ?= $(shell root-config --ldflags) -L$(CMSSW_BASE)/lib/$(SCRAM_ARCH) -lJHUGenMELAMELA
CLINGFLAGS ?= -f -Iinterface -I$(shell root-config --incdir) -I$(CMSSW_BASE)/src/JHUGenMELA/MELA/interface -rml --failOnWarnings -D__ACLIC__
VPATH ::= ./src ./interface
LIBS ::= cConstants_cpp.so FakeRates_cpp.so helpers_cpp.so MELAhelper_cpp.so
LIBPATHS ::= $(patsubst %,lib/%,$(LIBS))
DICT_SRCS ::= $(patsubst, %_cpp.so,%_cpp_ACLiC_dict.cxx,$(LIBPATHS))
DICT_OBJS ::= $(patsubst, %.cxx,%,$(DICT_SRCS))

### Main target
default: $(DICT_OBJS) $(LIBPATHS)
.PHONY: default

### Do not try to remake sources
Makefile:;
# C headers and sources
%.h:;
%.c:;
# C++ headers and sources
%.hpp:;
%.cpp:;

# secondary: never deleted, need not be rebuilt
.SECONDARY: $(DICT_SRCS)

### Build rules
# C object files
bin/%_c.o: src/%.c interface/%.h | bin
	$(CC) ${CFLAGS} -c $< -o $@
.NOTINTERMEDIATE: bin/cConstants_c.o

# C shared libraries are made from the corresponding object files
lib/%_c.so: bin/%_c.o | lib
	$(CC) -rdynamic -shared $< -o $@

# ROOT C++ shared libraries with dictionary
lib/%_cpp_ACLiC_dict.cxx lib/%_cpp_ACLiC_dict_rdict.pcm &: src/%.cpp interface/%.hpp src/LinkDef.h | lib
	rootcling $(CLINGFLAGS) $@ $^

lib/%_cpp_ACLiC_dict: lib/%_cpp_ACLiC_dict.cxx
	$(CXX) -I. $(CXXFLAGS) -c $< -o $@

lib/%_cpp.so: lib/%_cpp_ACLiC_dict | lib
	$(CXX) -rdynamic -shared $(LDFLAGS) $< -o $@

# C++ libraries are compiled with root from the source
# lib/%_cpp.so: src/%.cpp interface/%.hpp | lib
# 	root -l -e ".I ./interface" -e ".L $<+" -q
# 	mv src/$(*)_* lib/

bin lib:
	mkdir $@

### Utiltity phony targets
debug:
	@echo "LIBPATHS: $(LIBPATHS)"
.PHONY: debug

clean:
	-rm bin/* lib/*
.PHONY: clean
