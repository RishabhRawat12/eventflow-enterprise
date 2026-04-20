@echo off
set PY_INCLUDE="C:\Users\user\AppData\Local\Programs\Python\Python312\Include"
set PY_LIB="C:\Users\user\AppData\Local\Programs\Python\Python312\libs"

echo [BUILD] Generating C++ source from Cython...
cython --cplus astar.pyx -o astar.cpp

echo [BUILD] Compiling with G++...
g++ -shared -Wl,--export-all-symbols -O3 -fPIC -I%PY_INCLUDE% -L%PY_LIB% astar.cpp -o astar.pyd -lpython312

if exist astar.pyd (
    echo [SUCCESS] astar.pyd created.
) else (
    echo [FAILURE] Compilation failed.
)
