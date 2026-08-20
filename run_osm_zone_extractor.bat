@echo off
setlocal EnableExtensions EnableDelayedExpansion

title OSM Zone Extractor

rem ================================================================
rem Save as ASCII/UTF-8 without BOM, CRLF line endings. cmd.exe finds
rem labels by scanning CRLF lines; LF-only files fail mysteriously.
rem ================================================================

cd /d "%~dp0.."

set "PYTHON=.venv\Scripts\python.exe"
set "EXTRACTOR=src\osm_zone_extractor.py"
set "RESEARCH_DIR=research\market"
set "CACHE_DIR=.cache\osm"
set "ENV_FILE=.env"

set "KEY_SIGNUP=https://api.census.gov/data/key_signup.html"

set "CENSUS_API_KEY="

if exist "%ENV_FILE%" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        if /i "%%~A"=="CENSUS_API_KEY" set "CENSUS_API_KEY=%%~B"
    )
)

if not "%CENSUS_API_KEY_OVERRIDE%"=="" (
    set "CENSUS_API_KEY=%CENSUS_API_KEY_OVERRIDE%"
)

set "STARTUP_FAULT="

if not exist "%PYTHON%" set "STARTUP_FAULT=python"
if not exist "%EXTRACTOR%" set "STARTUP_FAULT=extractor"

goto MENU


rem ================================================================
rem MAIN MENU
rem ================================================================

:MENU
cls
echo ================================================================
echo                     OSM ZONE EXTRACTOR
echo ================================================================
echo.
echo Project: %CD%
echo.

if not "!STARTUP_FAULT!"=="" (
    echo   *** STARTUP PROBLEM ***
    echo.

    if "!STARTUP_FAULT!"=="python" (
        echo   Virtual-environment Python not found:
        echo     %CD%\%PYTHON%
        echo.
        echo   FIX:  python -m venv .venv
    )

    if "!STARTUP_FAULT!"=="extractor" (
        echo   Extractor script not found:
        echo     %CD%\%EXTRACTOR%
    )

    echo.
    echo ---------------------------------------------------------------
    echo.
)

if "!CENSUS_API_KEY!"=="" (
    echo   Census API key:  NOT SET   ^(US markets only^)
) else (
    call :MASK_KEY "!CENSUS_API_KEY!"
    echo   Census API key:  SET  ^(!MASKED!^)   ^(US markets only^)
)

echo.
echo ---------------------------------------------------------------
echo.
echo Reads administrative boundaries from OpenStreetMap. Everything
echo written is copied from a source; judgement fields stay NULL for
echo a research pass. Admin levels are NEVER guessed: a country must
echo have a verified profile or be given its levels explicitly.
echo.
echo VERIFIED COUNTRIES ^(just choose profile, no levels needed^):
echo.
echo   US CA GB IE DE FR ES IT AU NZ ZA KE NG GH TZ RW EG MA
echo.
echo ANY OTHER COUNTRY: use option 3 ^(probe^) first, then option 9
echo explains how to read the result. Thirty seconds, once ever.
echo.
echo ---------------------------------------------------------------
echo.
echo  1. Extract a market         ^(preview, writes nothing^)
echo  2. Extract a market         ^(write the file^)
echo  3. Probe a country's admin levels
echo  4. List verified countries with their levels
echo  5. List extracted markets
echo  6. Set the Census API key   ^(US only^)
echo  7. Diagnose setup
echo  8. Clear the download cache
echo  9. GUIDE: how admin levels work and how to choose them
echo  0. Exit
echo.
set "CHOICE="
set /p "CHOICE=Choose an option: "

if "%CHOICE%"=="1" goto EXTRACT_DRY
if "%CHOICE%"=="2" goto EXTRACT_WRITE
if "%CHOICE%"=="3" goto PROBE
if "%CHOICE%"=="4" goto LIST_COUNTRIES
if "%CHOICE%"=="5" goto LIST_MARKETS
if "%CHOICE%"=="6" goto SET_KEY
if "%CHOICE%"=="7" goto DIAGNOSE
if "%CHOICE%"=="8" goto CLEAR_CACHE
if "%CHOICE%"=="9" goto LEVEL_GUIDE
if "%CHOICE%"=="0" goto EXIT

echo.
echo Invalid option. Choose 0 to 9.
pause
goto MENU


rem ================================================================
rem OPTION 9: LEVEL GUIDE
rem ================================================================

:LEVEL_GUIDE
cls
echo ================================================================
echo            HOW ADMIN LEVELS WORK, AND HOW TO CHOOSE
echo ================================================================
echo.
echo OSM tags every administrative boundary with admin_level 2-11.
echo SMALLER NUMBER = BIGGER AREA:
echo.
echo   2   country
echo   4   state / province / region / KENYAN COUNTY
echo   6   county ^(US^) / district ^(DE,TZ^) / departement ^(FR^)
echo   8   municipality / city
echo.
echo The SAME NUMBER means DIFFERENT things per country. That is the
echo entire reason this script refuses to guess.
echo.
echo YOU NEED TWO LEVELS:
echo.
echo   BOUNDARY level = the whole market ^(one relation^)
echo   CHILD level    = the zones inside it ^(many relations^)
echo   Boundary must be a SMALLER number than child.
echo.
echo THE TWO COMMON PATTERNS:
echo.
echo   Pattern A ^(most countries^):  boundary 4, children 6
echo     us-vermont: Vermont ^(4^) -^> 14 counties ^(6^)
echo     tz-arusha:  Arusha region ^(4^) -^> districts ^(6^)
echo.
echo   Pattern B ^(flat countries, e.g. KENYA^):  boundary 2, children 4
echo     Kenyan counties sit at level 4 with NOTHING above them
echo     except the country. So the market is the WHOLE COUNTRY:
echo       slug ke-kenya, boundary 2, children 4 ^(47 counties^)
echo     There is NO valid ke-nairobi market at these levels:
echo     Nairobi IS one of the level-4 children.
echo.
echo HOW TO CHOOSE, STEP BY STEP:
echo.
echo   1. Is the country verified? ^(option 4 lists them^)
echo      YES -^> choose profile ^(option 1 in the extract screen^).
echo             DO NOT enter levels by hand. You are done.
echo      NO  -^> continue.
echo.
echo   2. Run option 3 ^(probe^). Read the counts:
echo      - the level whose count matches the country's official
echo        first-order subdivisions is your BOUNDARY level
echo      - the level below it holding the tier you want is CHILD
echo      - if the subdivisions sit at level 4 with no level above
echo        them but 2, you have a Kenya: boundary 2, child 4
echo.
echo   3. Extract with explicit levels, check the child COUNT
echo      against an official list ^(Wikipedia works^). Counts match
echo      -^> add the country to COUNTRY_PROFILES in
echo      %EXTRACTOR% so nobody probes it twice.
echo.
pause
goto MENU


rem ================================================================
rem OPTION 3: PROBE
rem ================================================================

:PROBE
cls
echo ================================================================
echo                 PROBE A COUNTRY'S ADMIN LEVELS
echo ================================================================
echo.

call :REQUIRE_TOOLING

if errorlevel 1 goto MENU

echo Reports how many relations exist at each admin level, with
echo three example names per level. Read it with option 9's guide.
echo.
echo Enter an ISO 3166-1 alpha-2 COUNTRY code ^(two letters, never a
echo state code^):
echo.
echo   Verified already ^(probe not needed^):
echo     US CA GB IE DE FR ES IT AU NZ ZA KE NG GH TZ RW EG MA
echo.
echo   Worth probing for new safari/tour markets:
echo     UG Uganda    BW Botswana    NA Namibia    ZM Zambia
echo     ZW Zimbabwe  MW Malawi      ET Ethiopia   MZ Mozambique
echo.
set "PROBE_CC="
set /p "PROBE_CC=Country code (blank to cancel): "

if "!PROBE_CC!"=="" goto MENU

echo !PROBE_CC!| findstr /r "^[A-Za-z][A-Za-z]$" >nul

if errorlevel 1 (
    echo.
    echo Not a two-letter country code. VT or NSW are subdivision
    echo codes, not countries.
    echo.
    pause
    goto MENU
)

echo.
echo Running one query per level, politely spaced. About half a
echo minute. Cached afterwards.
echo.

"%PYTHON%" "%EXTRACTOR%" --probe "!PROBE_CC!" --cache-dir "%CACHE_DIR%"

set "RESULT=!ERRORLEVEL!"

echo.

if not "!RESULT!"=="0" (
    call :EXPLAIN_RESULT !RESULT!
    echo.
    pause
    goto MENU
)

echo ---------------------------------------------------------------
echo.
echo NEXT: note the two levels, extract with option 1 choosing
echo "supply the levels explicitly", verify the child count, then
echo add the country to COUNTRY_PROFILES in %EXTRACTOR%.
echo.
pause
goto MENU


rem ================================================================
rem OPTION 4: LIST VERIFIED COUNTRIES
rem ================================================================

:LIST_COUNTRIES
cls

call :REQUIRE_TOOLING

if errorlevel 1 goto MENU

"%PYTHON%" "%EXTRACTOR%" --list-countries

echo.
pause
goto MENU


rem ================================================================
rem OPTION 6: SET THE CENSUS API KEY
rem ================================================================

:SET_KEY
cls
echo ================================================================
echo                   SET THE CENSUS API KEY
echo ================================================================
echo.
echo Needed only for UNITED STATES population figures. Non-US
echo markets ^(including ke-kenya^) ignore it entirely.
echo.
echo Free key: %KEY_SIGNUP%
echo.
echo Written to .env at the project root, never into source.
echo.

if not "!CENSUS_API_KEY!"=="" (
    call :MASK_KEY "!CENSUS_API_KEY!"
    echo Currently set: !MASKED!
    echo.
)

echo Leave blank to cancel.
echo.
set "NEW_KEY="
set /p "NEW_KEY=Census API key: "

if "!NEW_KEY!"=="" (
    echo.
    echo Cancelled.
    echo.
    pause
    goto MENU
)

echo !NEW_KEY!| findstr /r "^[0-9a-fA-F][0-9a-fA-F]*$" >nul

if errorlevel 1 (
    echo.
    echo That does not look like a Census key ^(long hex string^).
    echo.

    choice /c YN /m "Save it anyway"

    if errorlevel 2 (
        echo.
        echo Cancelled.
        echo.
        pause
        goto MENU
    )
)

call :WRITE_ENV_KEY "!NEW_KEY!"

if errorlevel 1 (
    echo.
    echo ERROR: Could not write %ENV_FILE%.
    echo.
    pause
    goto MENU
)

set "CENSUS_API_KEY=!NEW_KEY!"

echo.
echo Saved to %ENV_FILE%.
echo.

call :CHECK_GITIGNORE

echo.
pause
goto MENU


:WRITE_ENV_KEY
set "WEK_VALUE=%~1"
set "WEK_TEMP=%ENV_FILE%.tmp"

if exist "%WEK_TEMP%" del "%WEK_TEMP%" >nul 2>&1

if exist "%ENV_FILE%" (
    for /f "usebackq delims=" %%L in ("%ENV_FILE%") do (
        set "WEK_LINE=%%L"

        echo !WEK_LINE!| findstr /b /i "CENSUS_API_KEY=" >nul

        if errorlevel 1 echo !WEK_LINE!>>"%WEK_TEMP%"
    )
)

echo CENSUS_API_KEY=%WEK_VALUE%>>"%WEK_TEMP%"

if not exist "%WEK_TEMP%" exit /b 1

move /y "%WEK_TEMP%" "%ENV_FILE%" >nul 2>&1

if errorlevel 1 exit /b 1

exit /b 0


:CHECK_GITIGNORE
if not exist ".git" exit /b 0

set "IGNORED=0"

if exist ".gitignore" (
    findstr /b /c:".env" ".gitignore" >nul 2>&1

    if not errorlevel 1 set "IGNORED=1"
)

if "!IGNORED!"=="1" (
    echo .env is in .gitignore. The key will not be committed.
    exit /b 0
)

echo   *** WARNING: this is a git repo and .env is NOT ignored. ***
echo.

choice /c YN /m "Add .env to .gitignore now"

if errorlevel 2 (
    echo Not added. Do it before your next commit.
    exit /b 0
)

echo.>>".gitignore"
echo # Local secrets, never committed>>".gitignore"
echo .env>>".gitignore"

echo Added. Confirm with: git status

exit /b 0


:MASK_KEY
set "MK_VALUE=%~1"
set "MASKED="

if "%MK_VALUE%"=="" exit /b 0

set "MK_HEAD=%MK_VALUE:~0,4%"
set "MK_TAIL=%MK_VALUE:~-4%"

set "MASKED=%MK_HEAD%....%MK_TAIL%"

exit /b 0


rem ================================================================
rem OPTION 1 AND 2: EXTRACT
rem ================================================================

:EXTRACT_DRY
set "EXTRACT_MODE=dry"
goto EXTRACT_COMMON

:EXTRACT_WRITE
set "EXTRACT_MODE=write"
goto EXTRACT_COMMON

:EXTRACT_COMMON
cls
echo ================================================================

if "%EXTRACT_MODE%"=="dry" (
    echo                  EXTRACT - PREVIEW ONLY
) else (
    echo                   EXTRACT - WRITE FILE
)

echo ================================================================
echo.

call :REQUIRE_TOOLING

if errorlevel 1 goto MENU

echo A market slug is country-subdivision, lowercase, hyphenated.
echo THE SUBDIVISION MUST MATCH THE BOUNDARY TIER OF THE PROFILE:
echo.
echo   us-vermont     boundary = the STATE      ^(profile 4 -^> 6^)
echo   de-bayern      boundary = the STATE      ^(profile 4 -^> 6^)
echo   tz-arusha      boundary = the REGION     ^(profile 4 -^> 6^)
echo   ke-kenya       boundary = the COUNTRY    ^(profile 2 -^> 4^)
echo.
echo   KENYA-STYLE COUNTRIES: counties sit at level 4 with nothing
echo   above them, so the market is the WHOLE COUNTRY. Use ke-kenya.
echo   ke-nairobi is NOT valid here: Nairobi is one of the CHILDREN.
echo.

if "!CENSUS_API_KEY!"=="" (
    echo NOTE: No Census key set. Only affects US population.
    echo.
)

set "SLUG="
set /p "SLUG=Market slug (blank to cancel): "

if "!SLUG!"=="" goto MENU

echo !SLUG!| findstr /r "^[a-z][a-z]-[a-z0-9][a-z0-9-]*$" >nul

if errorlevel 1 (
    echo.
    echo Not a valid slug. Expected: two-letter country code, hyphen,
    echo subdivision in lowercase. Examples: us-vermont, ke-kenya,
    echo za-gauteng, tz-arusha.
    echo.
    pause
    goto MENU
)

rem Pull the country code off the slug for guidance below.
set "SLUG_CC=!SLUG:~0,2!"

set "LEVEL_ARGS="

echo.
echo ---------------------------------------------------------------
echo.
echo ADMIN LEVELS
echo.
echo   1. Use the verified profile for this country  ^(RECOMMENDED^)
echo   2. Supply the levels explicitly
echo   0. Cancel
echo.
echo Verified: US CA GB IE DE FR ES IT AU NZ ZA KE NG GH TZ RW EG MA
echo.
echo If your country is in that list, CHOOSE 1. Option 2 is only for
echo unverified countries ^(probe first, option 3^) or deliberate
echo overrides. Option 9 on the main menu explains how to choose.
echo.
set "LEVEL_MODE="
set /p "LEVEL_MODE=Choose: "

if "!LEVEL_MODE!"=="0" goto MENU

if "!LEVEL_MODE!"=="2" (
    echo.
    echo ---------------------------------------------------------------
    echo.
    echo EXPLICIT LEVELS - CHEAT SHEET
    echo.
    echo   Remember: SMALLER number = BIGGER area, and the boundary
    echo   number must be SMALLER than the child number.
    echo.
    echo   Verified profiles, for reference ^(choose 1 instead!^):
    echo     US 4-^>6   CA 4-^>6   GB 4-^>6   IE 6-^>7   DE 4-^>6
    echo     FR 4-^>6   ES 4-^>6   IT 4-^>6   AU 4-^>6   NZ 4-^>6
    echo     ZA 4-^>6   KE 2-^>4   NG 4-^>6   GH 4-^>6   TZ 4-^>6
    echo     RW 4-^>6   EG 4-^>6   MA 4-^>6
    echo.
    echo   Most countries: boundary 4, child 6.
    echo   Kenya-style flat countries: boundary 2, child 4.
    echo   Never guess a new country: probe it ^(option 3^) first.
    echo.

    if /i "!SLUG_CC!"=="ke" (
        echo   *** !SLUG! is KENYA, which HAS a verified profile
        echo   *** ^(boundary 2, children 4^). You almost certainly
        echo   *** want option 1 instead. Entering 4/6 here would
        echo   *** produce sub-counties masquerading as counties.
        echo.
    )

    set "B_LEVEL="
    set /p "B_LEVEL=Boundary admin level: "

    if "!B_LEVEL!"=="" (
        echo.
        echo Cancelled: no boundary level entered.
        pause
        goto MENU
    )

    echo !B_LEVEL!| findstr /r "^[0-9][0-9]*$" >nul

    if errorlevel 1 (
        echo.
        echo Not a number.
        pause
        goto MENU
    )

    set "C_LEVEL="
    set /p "C_LEVEL=Child admin level: "

    if "!C_LEVEL!"=="" (
        echo.
        echo Cancelled: no child level entered.
        pause
        goto MENU
    )

    echo !C_LEVEL!| findstr /r "^[0-9][0-9]*$" >nul

    if errorlevel 1 (
        echo.
        echo Not a number.
        pause
        goto MENU
    )

    if !B_LEVEL! GEQ !C_LEVEL! (
        echo.
        echo INVALID: boundary !B_LEVEL! is not smaller than child
        echo !C_LEVEL!. Smaller number = bigger area. A boundary at
        echo or below its children inverts the hierarchy.
        echo.
        pause
        goto MENU
    )

    set "LEVEL_ARGS=--boundary-level !B_LEVEL! --child-level !C_LEVEL!"

    echo.
    echo ZONE TYPES ^(optional, Enter to skip both^)
    echo.
    echo Valid: country, state, province, territory, county,
    echo district, municipality, city, town, village, borough,
    echo census_area, unincorporated_area, tribal_area,
    echo special_district, metropolitan_area, urban_area
    echo.
    set "B_TYPE="
    set /p "B_TYPE=Boundary zone type (Enter to skip): "

    if not "!B_TYPE!"=="" (
        set "LEVEL_ARGS=!LEVEL_ARGS! --boundary-zone-type !B_TYPE!"
    )

    set "C_TYPE="
    set /p "C_TYPE=Child zone type (Enter to skip): "

    if not "!C_TYPE!"=="" (
        set "LEVEL_ARGS=!LEVEL_ARGS! --child-zone-type !C_TYPE!"
    )
) else if not "!LEVEL_MODE!"=="1" (
    echo.
    echo Cancelled: "!LEVEL_MODE!" is not 0, 1 or 2.
    pause
    goto MENU
)

set "TARGET_DIR=%RESEARCH_DIR%\!SLUG!"
set "TARGET_FILE=!TARGET_DIR!\zones-generated.json"

echo.
echo ---------------------------------------------------------------
echo.

if "%EXTRACT_MODE%"=="write" (
    if exist "!TARGET_FILE!" (
        echo A generated file already exists:
        echo   !TARGET_FILE!
        echo.

        choice /c YN /m "Overwrite it"

        if errorlevel 2 (
            echo.
            echo Cancelled. Nothing written.
            echo.
            pause
            goto MENU
        )

        echo.
    )

    if not exist "!TARGET_DIR!" mkdir "!TARGET_DIR!" >nul 2>&1

    if not exist "!TARGET_DIR!" (
        echo ERROR: Could not create:
        echo   %CD%\!TARGET_DIR!
        echo.
        pause
        goto MENU
    )
)

echo Running. First pass for a country may take a minute or two,
echo mostly waiting politely on a free shared API.
echo.

if "%EXTRACT_MODE%"=="dry" (
    "%PYTHON%" "%EXTRACTOR%" --market "!SLUG!" !LEVEL_ARGS! --cache-dir "%CACHE_DIR%" --dry-run
) else (
    "%PYTHON%" "%EXTRACTOR%" --market "!SLUG!" !LEVEL_ARGS! --cache-dir "%CACHE_DIR%" --out "!TARGET_FILE!"
)

set "RESULT=!ERRORLEVEL!"

echo.

call :EXPLAIN_RESULT !RESULT!

echo.

if "%EXTRACT_MODE%"=="write" if "!RESULT!"=="0" (
    echo ---------------------------------------------------------------
    echo.
    echo NEXT STEP: the airport extractor reads this file's boundary
    echo relation, so run it with the SAME slug:
    echo.
    echo   src\run_osm_airport_extractor.bat   ^(slug: !SLUG!^)
    echo.
)

pause
goto MENU


rem ================================================================
rem OPTION 5: LIST EXTRACTED MARKETS
rem ================================================================

:LIST_MARKETS
cls
echo ================================================================
echo                    EXTRACTED MARKETS
echo ================================================================
echo.

if not exist "%RESEARCH_DIR%" (
    echo No research folder yet:
    echo   %CD%\%RESEARCH_DIR%
    echo.
    pause
    goto MENU
)

set "FOUND=0"

for /d %%D in ("%RESEARCH_DIR%\*") do call :LIST_ONE_MARKET "%%~fD" "%%~nxD"

if "!FOUND!"=="0" (
    echo No market folders found.
    echo.
)

pause
goto MENU


:LIST_ONE_MARKET
set "LOM_PATH=%~1"
set "LOM_NAME=%~2"
set "FOUND=1"

echo   !LOM_NAME!

if exist "!LOM_PATH!\zones-generated.json" (
    for %%F in ("!LOM_PATH!\zones-generated.json") do (
        set "LOM_SIZE=%%~zF"
        set /a LOM_KB=!LOM_SIZE! / 1024
        echo       zones-generated.json   ^(!LOM_KB! KB^)
    )

    findstr /c:"\"reference_strategy\": \"us-census\"" "!LOM_PATH!\zones-generated.json" >nul 2>&1

    if not errorlevel 1 (
        echo         Census reference path, tier 1 throughout.
    ) else (
        findstr /c:"\"reference_strategy\": \"generic\"" "!LOM_PATH!\zones-generated.json" >nul 2>&1

        if not errorlevel 1 (
            echo         Generic path: OSM points and population.
            echo         Population must be replaced before release.
        )
    )
) else (
    echo       ^(no generated zones yet^)
)

if exist "!LOM_PATH!\airports-generated.json" (
    echo       airports-generated.json   ^(airports extracted^)
)

if exist "!LOM_PATH!\02-geography-service-zones.json" (
    echo       02-geography-service-zones.json   ^(researched^)
)

echo.
exit /b 0


rem ================================================================
rem OPTION 7: DIAGNOSE
rem ================================================================

:DIAGNOSE
cls
echo ================================================================
echo                      DIAGNOSE SETUP
echo ================================================================
echo.

set "FAULTS=0"

echo [1] Virtual-environment Python
echo     %PYTHON%
echo.

if exist "%PYTHON%" (
    "%PYTHON%" --version

    if errorlevel 1 (
        echo     FAILED TO RUN. Usually a moved or partial venv.
        echo     FIX: rmdir /s /q .venv  then  python -m venv .venv
        set /a FAULTS+=1
    )
) else (
    echo     MISSING.  FIX: python -m venv .venv
    set /a FAULTS+=1
)

echo.
echo [2] Extractor script
echo     %EXTRACTOR%
echo.

if exist "%EXTRACTOR%" (
    echo     OK
    "%PYTHON%" "%EXTRACTOR%" --version 2>nul

    if errorlevel 1 (
        echo     But it did not run. Scroll up for a traceback.
        set /a FAULTS+=1
    )
) else (
    echo     MISSING
    set /a FAULTS+=1
)

echo.
echo [3] Census API key ^(US markets only^)
echo.

if "!CENSUS_API_KEY!"=="" (
    echo     NOT SET. Not a fault: non-US markets ignore it.
) else (
    call :MASK_KEY "!CENSUS_API_KEY!"
    echo     SET  ^(!MASKED!^), read from %ENV_FILE%
)

echo.
echo [4] Secret hygiene
echo.

if exist ".git" (
    if exist ".gitignore" (
        findstr /b /c:".env" ".gitignore" >nul 2>&1

        if errorlevel 1 (
            echo     .env is NOT in .gitignore in a git repo.
            echo     Choose 6 and accept the prompt.
            set /a FAULTS+=1
        ) else (
            echo     .env is in .gitignore. Good.
        )
    ) else (
        echo     No .gitignore. Create one with .env .venv/ .cache/
        set /a FAULTS+=1
    )
) else (
    echo     Not a git repository.
)

echo.
echo [5] Download cache: %CACHE_DIR%
echo.

if exist "%CACHE_DIR%" (
    set "CACHE_FILES=0"

    for %%F in ("%CACHE_DIR%\*") do set /a CACHE_FILES+=1

    echo     !CACHE_FILES! cached file^(s^).
) else (
    echo     Empty. First run downloads reference data.
)

echo.
echo [6] Network reachability
echo.

"%PYTHON%" -c "import urllib.request;urllib.request.urlopen('https://overpass-api.de/api/status',timeout=20);print('    Overpass API reachable.')" 2>nul

if errorlevel 1 (
    echo     Could not reach the Overpass API. It may just be busy;
    echo     the extractor retries and has a second mirror.
)

echo.
echo ================================================================

if "!FAULTS!"=="0" (
    echo   No blocking faults.
    set "STARTUP_FAULT="
) else (
    echo   !FAULTS! fault^(s^) found, each explained above.
)

echo ================================================================
echo.
pause
goto MENU


rem ================================================================
rem OPTION 8: CLEAR CACHE
rem ================================================================

:CLEAR_CACHE
cls
echo ================================================================
echo                   CLEAR THE DOWNLOAD CACHE
echo ================================================================
echo.

if not exist "%CACHE_DIR%" (
    echo Nothing cached.
    echo.
    pause
    goto MENU
)

echo Cached responses: %CD%\%CACHE_DIR%
echo Shared with the airport extractor. Clearing forces every
echo download again. Only worth it for stale or corrupt data.
echo.

choice /c YN /m "Clear it"

if errorlevel 2 goto MENU

rmdir /s /q "%CACHE_DIR%" >nul 2>&1

if exist "%CACHE_DIR%" (
    echo.
    echo Could not remove it. A file may be open elsewhere.
) else (
    echo.
    echo Cleared.
)

echo.
pause
goto MENU


rem ================================================================
rem SUBROUTINES
rem ================================================================

:REQUIRE_TOOLING

if not exist "%PYTHON%" (
    echo CANNOT RUN: venv Python not found: %CD%\%PYTHON%
    echo FIX:  python -m venv .venv
    echo.
    pause
    exit /b 1
)

if not exist "%EXTRACTOR%" (
    echo CANNOT RUN: extractor not found: %CD%\%EXTRACTOR%
    echo.
    pause
    exit /b 1
)

exit /b 0


:EXPLAIN_RESULT
set "CODE=%~1"

if "%CODE%"=="0" (
    echo RESULT: COMPLETED
    echo.
    echo Read the run log rather than assuming success. Warnings that
    echo matter:
    echo.
    echo   "no admin_centre member"   zone has no centre point; null
    echo                              on purpose, common outside US
    echo   "no containment filter"    a bordering district may have
    echo                              slipped in. CHECK THE CHILD
    echo                              COUNT: Kenya should show 47
    echo   "Duplicate zone ID"        two districts share a name
    echo.
    echo A null is the extractor declining to guess. That is its job.
    exit /b 0
)

if "%CODE%"=="1" (
    echo RESULT: USAGE PROBLEM
    echo.
    echo The extractor refused to start. Usually: no verified profile
    echo and no levels supplied. FIX: option 3 to probe, option 9 to
    echo read the result, then extract with explicit levels. Option 4
    echo lists countries that need neither.
    exit /b 0
)

if "%CODE%"=="2" (
    echo RESULT: EXTRACTION FAILED
    echo.
    echo Common causes:
    echo   - Overpass busy or down: retry shortly.
    echo   - Name did not resolve: OSM uses local spelling ^(Bayern
    echo     not Bavaria^). Try local name or --relation-id.
    echo   - Wrong admin level for this country: option 3 shows what
    echo     exists. For Kenya use the profile ^(2 -^> 4^) with slug
    echo     ke-kenya, never ke-nairobi.
    exit /b 0
)

if "%CODE%"=="9009" (
    echo RESULT: COMMAND NOT FOUND. Choose 7 to diagnose.
    exit /b 0
)

echo RESULT: UNEXPECTED EXIT CODE %CODE%
echo Scroll up for a traceback; that is a bug in the extractor, not
echo your input.

exit /b 0


:EXIT
echo.
echo Closing.
endlocal
exit /b 0