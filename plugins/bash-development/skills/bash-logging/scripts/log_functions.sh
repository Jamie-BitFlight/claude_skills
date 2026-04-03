#!/usr/bin/env sh
# shellcheck disable=SC2034,SC2119,SC2120,SC1091

# bin/library/log_functions.sh
# A consolidated script combining logging functions with enhanced styling and utilities.

# Prevent multiple sourcing
: "${SHLOCKSMITH__LOG_FUNCTIONS_LOADED:=1}"

# ===============================
# Color and Emoji Variables
# ===============================
# Text formatting
TEXT_UNDERLINE="\033[4m"
TEXT_STRIKETHROUGH="\033[9m"
TEXT_DIM="\033[2m"
TEXT_BLINK="\033[5m"
TEXT_REVERSE="\033[7m"
TEXT_HIDDEN="\033[8m"
TEXT_DOUBLE_UNDERLINE="\033[21m"
TEXT_OVERLINE="\033[53m"

# Box Drawing Variables
BOX_HORIZONTAL="${BOX_HORIZONTAL:-$(printf '\342\224\200')}"                                 # ─
BOX_VERTICAL="${BOX_VERTICAL:-$(printf '\342\224\202')}"                                     # │
BOX_CORNER_TOP_LEFT="${BOX_CORNER_TOP_LEFT:-$(printf '\342\224\214')}"                       # ┌
BOX_CORNER_TOP_RIGHT="${BOX_CORNER_TOP_RIGHT:-$(printf '\342\224\220')}"                     # ┐
BOX_CORNER_BOTTOM_LEFT="${BOX_CORNER_BOTTOM_LEFT:-$(printf '\342\224\224')}"                 # └
BOX_CORNER_BOTTOM_RIGHT="${BOX_CORNER_BOTTOM_RIGHT:-$(printf '\342\224\230')}"               # ┘
BOX_TEE_TOP="${BOX_TEE_TOP:-$(printf '\342\224\234')}"                                       # ┬
BOX_TEE_BOTTOM="${BOX_TEE_BOTTOM:-$(printf '\342\224\244')}"                                 # ┴
BOX_TEE_LEFT="${BOX_TEE_LEFT:-$(printf '\342\224\234')}"                                     # ├
BOX_TEE_RIGHT="${BOX_TEE_RIGHT:-$(printf '\342\224\244')}"                                   # ┤
BOX_CROSS="${BOX_CROSS:-$(printf '\342\224\274')}"                                           # ┼
BOX_DOUBLE_HORIZONTAL="${BOX_DOUBLE_HORIZONTAL:-$(printf '\342\225\220')}"                   # ═
BOX_DOUBLE_VERTICAL="${BOX_DOUBLE_VERTICAL:-$(printf '\342\225\221')}"                       # ║
BOX_DOUBLE_CORNER_TOP_LEFT="${BOX_DOUBLE_CORNER_TOP_LEFT:-$(printf '\342\225\224')}"         # ╔
BOX_DOUBLE_CORNER_TOP_RIGHT="${BOX_DOUBLE_CORNER_TOP_RIGHT:-$(printf '\342\225\227')}"       # ╗
BOX_DOUBLE_CORNER_BOTTOM_LEFT="${BOX_DOUBLE_CORNER_BOTTOM_LEFT:-$(printf '\342\225\232')}"   # ╚
BOX_DOUBLE_CORNER_BOTTOM_RIGHT="${BOX_DOUBLE_CORNER_BOTTOM_RIGHT:-$(printf '\342\225\235')}" # ╝
BOX_DOUBLE_TEE_TOP="${BOX_DOUBLE_TEE_TOP:-$(printf '\342\225\240')}"                         # ╦
BOX_DOUBLE_TEE_BOTTOM="${BOX_DOUBLE_TEE_BOTTOM:-$(printf '\342\225\243')}"                   # ╩
BOX_DOUBLE_TEE_LEFT="${BOX_DOUBLE_TEE_LEFT:-$(printf '\342\225\242')}"                       # ╠
BOX_DOUBLE_TEE_RIGHT="${BOX_DOUBLE_TEE_RIGHT:-$(printf '\342\225\241')}"                     # ╣
BOX_DOUBLE_CROSS="${BOX_DOUBLE_CROSS:-$(printf '\342\225\244')}"                             # ╬
# Cursor movement
CURSOR_UP="\033[1A"
CURSOR_DOWN="\033[1B"
CURSOR_RIGHT="\033[1C"
CURSOR_LEFT="\033[1D"

# Bar Chart Vertical Variables
BAR_CHART_VERT_1="${BAR_CHART_VERT_1:-$(printf '\342\226\201')}" # ▁
BAR_CHART_VERT_2="${BAR_CHART_VERT_2:-$(printf '\342\226\202')}" # ▂
BAR_CHART_VERT_3="${BAR_CHART_VERT_3:-$(printf '\342\226\203')}" # ▃
BAR_CHART_VERT_4="${BAR_CHART_VERT_4:-$(printf '\342\226\204')}" # ▄
BAR_CHART_VERT_5="${BAR_CHART_VERT_5:-$(printf '\342\226\205')}" # ▅
BAR_CHART_VERT_6="${BAR_CHART_VERT_6:-$(printf '\342\226\206')}" # ▆

# Bar Char Horizontal Variables
BAR_CHART_HORIZ_1="${BAR_CHART_HORIZ_1:-$(printf '\342\226\207')}" # ▇
BAR_CHART_HORIZ_2="${BAR_CHART_HORIZ_2:-$(printf '\342\226\210')}" # █
BAR_CHART_HORIZ_3="${BAR_CHART_HORIZ_3:-$(printf '\342\226\211')}" # ▉
BAR_CHART_HORIZ_4="${BAR_CHART_HORIZ_4:-$(printf '\342\226\212')}" # ▊
BAR_CHART_HORIZ_5="${BAR_CHART_HORIZ_5:-$(printf '\342\226\213')}" # ▋
BAR_CHART_HORIZ_6="${BAR_CHART_HORIZ_6:-$(printf '\342\226\214')}" # ▌
BAR_CHART_HORIZ_7="${BAR_CHART_HORIZ_7:-$(printf '\342\226\215')}" # ▍
BAR_CHART_HORIZ_8="${BAR_CHART_HORIZ_8:-$(printf '\342\226\216')}" # ▎
BAR_CHART_HORIZ_9="${BAR_CHART_HORIZ_9:-$(printf '\342\226\217')}" # ▏

COLOR_RGB_ORANGE="\033[38;2;255;128;0m" # Another orange
COLOR_256_ORANGE="\033[38;5;208m"       # A bright orange

# Color and Emoji Variables

# Set or use the default values for the color variables
COLOR_RED="${COLOR_RED:-$(printf '\033[0;31m')}"
COLOR_GREEN="${COLOR_GREEN:-$(printf '\033[0;32m')}"
COLOR_YELLOW="${COLOR_YELLOW:-$(printf '\033[0;33m')}"
COLOR_BLUE="${COLOR_BLUE:-$(printf '\033[0;34m')}"
COLOR_MAGENTA="${COLOR_MAGENTA:-$(printf '\033[0;35m')}"
COLOR_CYAN="${COLOR_CYAN:-$(printf '\033[0;36m')}"
COLOR_WHITE="${COLOR_WHITE:-$(printf '\033[0;37m')}"
NC="${NC:-$(printf '\033[0m')}" # No Color
COLOR_BOLD="${COLOR_BOLD:-$(printf '\033[1m')}"
COLOR_GREY="${COLOR_GREY:-$(printf '\033[30m')}"
COLOR_BLACK="${COLOR_BLACK:-$(printf '\033[0;30m')}"

# Bold color codes
COLOR_BOLD_RED="${COLOR_BOLD_RED:-$(printf '\033[1;31m')}"
COLOR_BOLD_GREEN="${COLOR_BOLD_GREEN:-$(printf '\033[1;32m')}"
COLOR_BOLD_YELLOW="${COLOR_BOLD_YELLOW:-$(printf '\033[1;33m')}"
COLOR_BOLD_BLUE="${COLOR_BOLD_BLUE:-$(printf '\033[1;34m')}"
COLOR_BOLD_MAGENTA="${COLOR_BOLD_MAGENTA:-$(printf '\033[1;35m')}"
COLOR_BOLD_CYAN="${COLOR_BOLD_CYAN:-$(printf '\033[1;36m')}"
COLOR_BOLD_WHITE="${COLOR_BOLD_WHITE:-$(printf '\033[1;37m')}"

# Bright color codes
COLOR_BRIGHT_BLACK="${COLOR_BRIGHT_BLACK:-$(printf '\033[0;90m')}"
COLOR_BRIGHT_RED="${COLOR_BRIGHT_RED:-$(printf '\033[0;91m')}"
COLOR_BRIGHT_GREEN="${COLOR_BRIGHT_GREEN:-$(printf '\033[0;92m')}"
COLOR_BRIGHT_YELLOW="${COLOR_BRIGHT_YELLOW:-$(printf '\033[0;93m')}"
COLOR_BRIGHT_BLUE="${COLOR_BRIGHT_BLUE:-$(printf '\033[0;94m')}"
COLOR_BRIGHT_MAGENTA="${COLOR_BRIGHT_MAGENTA:-$(printf '\033[0;95m')}"
COLOR_BRIGHT_CYAN="${COLOR_BRIGHT_CYAN:-$(printf '\033[0;96m')}"
COLOR_BRIGHT_WHITE="${COLOR_BRIGHT_WHITE:-$(printf '\033[0;97m')}"

# Dim Color Codes
COLOR_DIM_BLACK="${COLOR_DIM_BLACK:-$(printf '\033[2;30m')}"
COLOR_DIM_RED="${COLOR_DIM_RED:-$(printf '\033[2;31m')}"
COLOR_DIM_GREEN="${COLOR_DIM_GREEN:-$(printf '\033[2;32m')}"
COLOR_DIM_YELLOW="${COLOR_DIM_YELLOW:-$(printf '\033[2;33m')}"
COLOR_DIM_BLUE="${COLOR_DIM_BLUE:-$(printf '\033[2;34m')}"
COLOR_DIM_MAGENTA="${COLOR_DIM_MAGENTA:-$(printf '\033[2;35m')}"
COLOR_DIM_CYAN="${COLOR_DIM_CYAN:-$(printf '\033[2;36m')}"
COLOR_DIM_WHITE="${COLOR_DIM_WHITE:-$(printf '\033[2;37m')}"

# Background color codes
COLOR_BG_BLACK="${COLOR_BG_BLACK:-$(printf '\033[1;40m')}"
COLOR_BG_RED="${COLOR_BG_RED:-$(printf '\033[1;41m')}"
COLOR_BG_GREEN="${COLOR_BG_GREEN:-$(printf '\033[1;42m')}"
COLOR_BG_YELLOW="${COLOR_BG_YELLOW:-$(printf '\033[1;43m')}"
COLOR_BG_BLUE="${COLOR_BG_BLUE:-$(printf '\033[1;44m')}"
COLOR_BG_MAGENTA="${COLOR_BG_MAGENTA:-$(printf '\033[1;45m')}"
COLOR_BG_CYAN="${COLOR_BG_CYAN:-$(printf '\033[1;46m')}"
COLOR_BG_WHITE="${COLOR_BG_WHITE:-$(printf '\033[1;47m')}"

# Reset color codes
COLOR_RESET="${COLOR_RESET:-$(printf '\033[0m')}"

# Other color variables
COLOR_ITALIC="${COLOR_ITALIC:-$(printf '\033[3m')}"
COLOR_ITALIC_END="${COLOR_ITALIC_END:-$(printf '\033[23m')}"
CLEAR_SCREEN="${CLEAR_SCREEN:-$(tput rc 2>/dev/null || printf '')}"

# Weather and Nature
SUN_ICON="${SUN_ICON:-$(printf '\342\230\200')}"           # ☀ Sun
CLOUD_ICON="${CLOUD_ICON:-$(printf '\342\230\201')}"       # ☁ Cloud
UMBRELLA_ICON="${UMBRELLA_ICON:-$(printf '\342\230\202')}" # ☂ Umbrella
SNOWMAN_ICON="${SNOWMAN_ICON:-$(printf '\342\230\203')}"   # ☃ Snowman
COMET_ICON="${COMET_ICON:-$(printf '\342\230\204')}"       # ☄ Comet
SHAMROCK_ICON="${SHAMROCK_ICON:-$(printf '\342\230\230')}" # ☘ Shamrock

# Status and Interface
CHECKBOX_EMPTY="${CHECKBOX_EMPTY:-$(printf '\342\230\220')}"     # ☐ Empty Checkbox
CHECKBOX_CHECKED="${CHECKBOX_CHECKED:-$(printf '\342\230\221')}" # ☑ Checked Checkbox
CHECKBOX_CROSS="${CHECKBOX_CROSS:-$(printf '\342\230\222')}"     # ☒ Crossed Checkbox
WARNING_ICON="${WARNING_ICON:-$(printf '\342\232\240')}"         # ⚠ Warning
LIGHTNING_ICON="${LIGHTNING_ICON:-$(printf '\342\232\241')}"     # ⚡ Lightning

# Miscellaneous Objects
PHONE_ICON="${PHONE_ICON:-$(printf '\342\230\216')}"   # ☎ Phone
COFFEE_ICON="${COFFEE_ICON:-$(printf '\342\230\225')}" # ☕ Coffee
GEAR_ICON="${GEAR_ICON:-$(printf '\342\232\231')}"     # ⚙ Gear
ANCHOR_ICON="${ANCHOR_ICON:-$(printf '\342\232\223')}" # ⚓ Anchor
SCALES_ICON="${SCALES_ICON:-$(printf '\342\232\226')}" # ⚖ Scales

# Celestial and Zodiac
MOON_ICON="${MOON_ICON:-$(printf '\342\230\275')}"       # ☽ Moon
MERCURY_ICON="${MERCURY_ICON:-$(printf '\342\230\277')}" # ☿ Mercury
VENUS_ICON="${VENUS_ICON:-$(printf '\342\231\200')}"     # ♀ Venus
MARS_ICON="${MARS_ICON:-$(printf '\342\231\202')}"       # ♂ Mars
JUPITER_ICON="${JUPITER_ICON:-$(printf '\342\231\203')}" # ♃ Jupiter

# Games and Sports
DICE_ONE="${DICE_ONE:-$(printf '\342\232\200')}"           # ⚀ Die Face-1
DICE_TWO="${DICE_TWO:-$(printf '\342\232\201')}"           # ⚁ Die Face-2
DICE_THREE="${DICE_THREE:-$(printf '\342\232\202')}"       # ⚂ Die Face-3
SOCCER_ICON="${SOCCER_ICON:-$(printf '\342\232\275')}"     # ⚽ Soccer Ball
BASEBALL_ICON="${BASEBALL_ICON:-$(printf '\342\232\276')}" # ⚾ Baseball

# Music
MUSIC_NOTE="${MUSIC_NOTE:-$(printf '\342\231\251')}"   # ♩ Music Note
EIGHTH_NOTE="${EIGHTH_NOTE:-$(printf '\342\231\252')}" # ♪ Eighth Note
BEAMED_NOTE="${BEAMED_NOTE:-$(printf '\342\231\253')}" # ♫ Beamed Notes
SHARP_ICON="${SHARP_ICON:-$(printf '\342\231\257')}"   # ♯ Sharp

# Recycling and Environment
RECYCLE_ICON="${RECYCLE_ICON:-$(printf '\342\231\273')}"       # ♻ Recycling
WHEELCHAIR_ICON="${WHEELCHAIR_ICON:-$(printf '\342\231\277')}" # ♿ Wheelchair

# Buildings and Places
CHURCH_ICON="${CHURCH_ICON:-$(printf '\342\233\252')}"     # ⛪ Church
FOUNTAIN_ICON="${FOUNTAIN_ICON:-$(printf '\342\233\262')}" # ⛲ Fountain
TENT_ICON="${TENT_ICON:-$(printf '\342\233\272')}"         # ⛺ Tent
GAS_PUMP="${GAS_PUMP:-$(printf '\342\233\275')}"           # ⛽ Fuel Pump

# Icon Variables
INFORMATION_ICON="${INFORMATION_ICON:-$(printf '\342\204\271')}"       # ℹ Information
GEAR_ICON="${GEAR_ICON:-$(printf '\342\232\231')}"                     # ⚙ Gear
TOOLS_ICON="${TOOLS_ICON:-$(printf '\342\232\222')}"                   # ⚒ Tools
ITALIC_CROSS_ICON="${ITALIC_CROSS_ICON:-$(printf '\342\234\227')}"     # ✗ Italic Cross
SKULL_ICON="${SKULL_ICON:-$(printf '\xE2\x98\xA0')}"                   # ☠ Skull and Crossbones
HAZARD_ICON="${HAZARD_ICON:-$(printf '\342\232\240')}"                 # ⚠ Hazard
BALLOT_TICK_ICON="${BALLOT_TICK_ICON:-$(printf '\342\230\221')}"       # ☑ Ballot Box With Tick
BALLOT_CROSS_ICON="${BALLOT_CROSS_ICON:-$(printf '\342\230\222')}"     # ☒ Ballot Box With X
BALLOT_EMPTY_ICON="${BALLOT_EMPTY_ICON:-$(printf '\342\230\220')}"     # ☐ Ballot Box Empty
ELIPSIS_ICON="${ELIPSIS_ICON:-$(printf '\342\200\246')}"               # … Ellipsis
UMBRELLA_ICON="${UMBRELLA_ICON:-$(printf '\342\230\202')}"             # ☂ Umbrella
CIRCLE_BULLET_ICON="${CIRCLE_BULLET_ICON:-$(printf '\342\232\254')}"   # ⚬ Circle Bullet
HIDDEN_CIRCLE_ICON="${HIDDEN_CIRCLE_ICON:-$(printf '\342\227\214')}"   # ◌ Hidden Circle
VISIBLE_CIRCLE_ICON="${VISIBLE_CIRCLE_ICON:-$(printf '\342\227\213')}" # ○ Visible Circle
TRIANGLE_ICON="${TRIANGLE_ICON:-$(printf '\342\226\276')}"             # ▾ Triangle
CROSS_ICON="${CROSS_ICON:-$(printf '\342\230\223')}"                   # ☓ Cross
BOLD_CROSS_ICON="${BOLD_CROSS_ICON:-$(printf '\342\234\226')}"         # ✖ Bold Cross
CHECK_ICON="${CHECK_ICON:-$(printf '\342\234\223')}"                   # ✓ Check
SWORDS_ICON="${SWORDS_ICON:-$(printf '\342\232\224')}"                 # ⚔ Swords
SWERVE_ICON="${SWERVE_ICON:-$(printf '\342\230\241')}"                 # ☡ Swerve
STAR_OPEN_ICON="${STAR_OPEN_ICON:-$(printf '\342\230\206')}"           # ☆ Star Open
STAR_FILLED_ICON="${STAR_FILLED_ICON:-$(printf '\342\230\205')}"       # ★ Star Filled
LIGHTNING_ICON="${LIGHTNING_ICON:-$(printf '\342\232\241')}"           # ⚡ Lightning
FLAG_ICON="${FLAG_ICON:-$(printf '\342\232\221')}"                     # ⚑ Flag
HAND_PEN_ICON="${HAND_PEN_ICON:-$(printf '\342\234\215')}"             # ✍ Hand Pen
PENCIL_ICON="${PENCIL_ICON:-$(printf '\342\234\217')}"                 # ✏ Pencil

# Marks and Symbols (reliable single-width)
CHECK_MARK="${CHECK_MARK:-$(printf '\342\234\223')}"   # ✓ Check mark (U+2713)
HEAVY_CHECK="${HEAVY_CHECK:-$(printf '\342\234\224')}" # ✔ Heavy check (U+2714)
CROSS_MARK="${CROSS_MARK:-$(printf '\342\234\227')}"   # ✗ Ballot X (U+2717)
HEAVY_CROSS="${HEAVY_CROSS:-$(printf '\342\234\226')}" # ✖ Heavy multiplication X (U+2716)
PLUS_SIGN="${PLUS_SIGN:-$(printf '\342\234\232')}"     # ✚ Heavy Greek cross (U+271A)

# Punctuation and Bullets
BULLET="${BULLET:-$(printf '\342\200\242')}"                   # • Bullet (U+2022)
TRIANGLE_BULLET="${TRIANGLE_BULLET:-$(printf '\342\200\243')}" # ‣ Triangular bullet (U+2023)
WHITE_BULLET="${WHITE_BULLET:-$(printf '\342\227\246')}"       # ◦ White bullet (U+25E6)
DOUBLE_ANGLE="${DOUBLE_ANGLE:-$(printf '\342\200\273')}"       # ※ Reference mark (U+203B)

# Shapes (generally safe)
BLACK_SQUARE="${BLACK_SQUARE:-$(printf '\342\226\240')}"   # ■ Black square (U+25A0)
WHITE_SQUARE="${WHITE_SQUARE:-$(printf '\342\226\241')}"   # □ White square (U+25A1)
BLACK_DIAMOND="${BLACK_DIAMOND:-$(printf '\342\227\206')}" # ◆ Black diamond (U+25C6)
WHITE_DIAMOND="${WHITE_DIAMOND:-$(printf '\342\227\207')}" # ◇ White diamond (U+25C7)
BLACK_CIRCLE="${BLACK_CIRCLE:-$(printf '\342\227\217')}"   # ● Black circle (U+25CF)
WHITE_CIRCLE="${WHITE_CIRCLE:-$(printf '\342\227\213')}"   # ○ White circle (U+25CB)

# Arrows (from Dingbats, usually safe)
ARROW_RIGHT="${ARROW_RIGHT:-$(printf '\342\236\234')}"               # ➜ Heavy round-tipped rightwards arrow (U+279C)
ARROW_RIGHT_SIMPLE="${ARROW_RIGHT_SIMPLE:-$(printf '\342\206\222')}" # → Rightwards arrow (U+2192)
ARROW_LEFT_SIMPLE="${ARROW_LEFT_SIMPLE:-$(printf '\342\206\220')}"   # ← Leftwards arrow (U+2190)

SHLOCKSMITH_PROJECT_ICON="${SHLOCKSMITH_PROJECT_ICON:-${COFFEE_ICON}}"
PACKAGE_ICON="${PACKAGE_ICON:-"📦"}"
MANDALA_ICON="${MANDALA_ICON:-"⚛"}"
SEXTILE_ICON="${SEXTILE_ICON:-"⚶"}"

# Emoji Variables
ERROR_EMOJI="${ERROR_EMOJI:-${BOLD_CROSS_ICON}}"
FAIL_EMOJI="${FAIL_EMOJI:-${BALLOT_CROSS_ICON}}"
INFO_EMOJI="${INFO_EMOJI:-${INFORMATION_ICON}}"
NOTICE_EMOJI="${NOTICE_EMOJI:-${FLAG_ICON}}"
SECTION_EMOJI="${SECTION_EMOJI:-${PACKAGE_ICON}}"
DONE_EMOJI="${DONE_EMOJI:-${CHECK_ICON}}"
PASS_EMOJI="${PASS_EMOJI:-${BALLOT_TICK_ICON}}"
USAGE_EMOJI="${USAGE_EMOJI:-${PENCIL_ICON}}"
WARNING_EMOJI="${WARNING_EMOJI:-${HAZARD_ICON}}"
WARN_EMOJI="${WARN_EMOJI:-"${WARNING_EMOJI}"}"

# Mapped Icon Labels
SUCCESS_ICON="${SUCCESS_ICON:-${CHECK_ICON}}"
SUCCESS_COLOR="${SUCCESS_COLOR:-${COLOR_BOLD_GREEN}}"

FAILURE_ICON="${FAILURE_ICON:-${CROSS_ICON}}"
FAILURE_COLOR="${FAILURE_COLOR:-${COLOR_BRIGHT_RED}}"

FATAL_ICON="${FATAL_ICON:-${SKULL_ICON}}"
FATAL_COLOR="${FATAL_COLOR:-${COLOR_BOLD_RED}}"

WARNING_ICON="${WARNING_ICON:-${HAZARD_ICON}}"
WARNING_COLOR="${WARNING_COLOR:-${COLOR_BOLD_YELLOW}}"

ERROR_ICON="${ERROR_ICON:-${ITALIC_CROSS_ICON}}"
ERROR_COLOR="${ERROR_COLOR:-${COLOR_BOLD_RED}}"

DEBUG_ICON="${DEBUG_ICON:-${GEAR_ICON}}"
DEBUG_COLOR="${DEBUG_COLOR:-${COLOR_BOLD_BLUE}}"

INFO_ICON="${INFO_ICON:-${INFORMATION_ICON}}"
INFO_COLOR="${INFO_COLOR:-${COLOR_RESET}}"

START_ICON="${START_ICON:-${STAR_FILLED_ICON}}"
START_COLOR="${START_COLOR:-${COLOR_BRIGHT_CYAN}}"

OPTION_ICON="${OPTION_ICON:-${VISIBLE_CIRCLE_ICON}}"
OPTION_COLOR="${OPTION_COLOR:-${COLOR_BRIGHT_BLUE}}"

STEP_INFO_ICON="${STEP_INFO_ICON:-${SWERVE_ICON}}"
STEP_INFO_COLOR="${STEP_INFO_COLOR:-${COLOR_MAGENTA}}"

STEP_START_ICON="${STEP_START_ICON:-${SEXTILE_ICON}}"
STEP_START_COLOR="${STEP_START_COLOR:-${COLOR_BRIGHT_MAGENTA}}"

STEP_ICON="${STEP_ICON:-${STAR_OPEN_ICON}}"
STEP_COLOR="${STEP_COLOR:-${COLOR_CYAN}}"

STEP_LOG_COMMAND_ICON="${STEP_LOG_COMMAND_ICON:-"${GEAR_ICON}"}"
STEP_LOG_COMMAND_COLOR="${STEP_LOG_COMMAND_COLOR:-"${COLOR_BOLD}${COLOR_BRIGHT_CYAN}"}"

STEP_LOG_OUTPUT_ICON="${STEP_LOG_OUTPUT_ICON:-${ELIPSIS_ICON}}"
STEP_LOG_OUTPUT_COLOR="${STEP_LOG_OUTPUT_COLOR:-${COLOR_RESET}}"

STEP_DONE_ICON="${STEP_DONE_ICON:-${HEAVY_CHECK}}"
STEP_DONE_COLOR="${STEP_DONE_COLOR:-${COLOR_DIM_YELLOW}}"

PASS_ICON="${PASS_ICON:-${BALLOT_TICK_ICON}}"
PASS_COLOR="${PASS_COLOR:-${COLOR_BOLD_GREEN}}"

FAIL_ICON="${FAIL_ICON:-${BALLOT_CROSS_ICON}}"
FAIL_COLOR="${FAIL_COLOR:-${COLOR_BOLD_RED}}"

SKIP_ICON="${SKIP_ICON:-${HIDDEN_CIRCLE_ICON}}"
SKIP_COLOR="${SKIP_COLOR:-${COLOR_BRIGHT_YELLOW}}"

IN_PROGRESS_ICON="${IN_PROGRESS_ICON:-${CIRCLE_BULLET_ICON}}"
IN_PROGRESS_COLOR="${IN_PROGRESS_COLOR:-${COLOR_BRIGHT_BLUE}}"

DONE_ICON="${DONE_ICON:-${FLAG_ICON}}"
DONE_COLOR="${DONE_COLOR:-${COLOR_BOLD_GREEN}}"

MAINTENANCE_ICON="${MAINTENANCE_ICON:-${TOOLS_ICON}}"
MAINTENANCE_COLOR="${MAINTENANCE_COLOR:-${COLOR_BRIGHT_YELLOW}}"

PROBLEM_ICON="${PROBLEM_ICON:-${UMBRELLA_ICON}}"
PROBLEM_COLOR="${PROBLEM_COLOR:-${COLOR_BOLD_RED}}"

NOTICE_ICON="${NOTICE_ICON:-${LIGHTNING_ICON}}"
NOTICE_COLOR="${NOTICE_COLOR:-${COLOR_BRIGHT_MAGENTA}}"

RESULTS_ICON="${RESULTS_ICON:-${PENCIL_ICON}}"
RESULTS_COLOR="${RESULTS_COLOR:-${COLOR_BRIGHT_CYAN}}"

QUESTION_ICON="${QUESTION_ICON:-${HAND_PEN_ICON}}"
QUESTION_COLOR="${QUESTION_COLOR:-${COLOR_BRIGHT_GREEN}}"

# Logging colors
LOG_LEVEL_FOREGROUND="\033[38;2;135;206;235m" # Sky Blue (#87CEEB)
LOG_LEVEL_BACKGROUND=""
LOG_TIME_FOREGROUND="\033[38;2;0;255;0m" # Green (#00FF00)
LOG_TIME_BACKGROUND=""
LOG_PREFIX_FOREGROUND="\033[38;2;255;255;0m" # Bright Yellow (#FFFF00)
LOG_PREFIX_BACKGROUND=""
LOG_MESSAGE_FOREGROUND="\033[38;2;255;255;255m" # White (#FFFFFF)
LOG_MESSAGE_BACKGROUND=""
LOG_KEY_FOREGROUND="\033[1;38;2;202;73;73m" # Bold Orange (#ca4949)
LOG_KEY_BACKGROUND=""
LOG_VALUE_FOREGROUND="\033[38;2;132;100;196m" # Purple (#8464c4)
LOG_VALUE_BACKGROUND=""
LOG_SEPARATOR_FOREGROUND="\033[38;2;255;255;255m" # White (#FFFFFF)
LOG_SEPARATOR_BACKGROUND=""
LOG_BLOCK_TEXT_FOREGROUND="\033[38;2;75;155;230m" # OneHalf Blue (#4B9BE6)

GUM_LOG_LEVEL_FOREGROUND="#87CEEB" # Sky Blue (SecondaryTextColor)
GUM_LOG_LEVEL_BACKGROUND=""
GUM_LOG_TIME_FOREGROUND="#00FF00" # Green (TertiaryTextColor)
GUM_LOG_TIME_BACKGROUND=""
GUM_LOG_PREFIX_FOREGROUND="#FFFF00" # Bright Yellow
GUM_LOG_PREFIX_BACKGROUND=""
GUM_LOG_MESSAGE_FOREGROUND="#FFFFFF" # White (PrimaryTextColor)
GUM_LOG_MESSAGE_BACKGROUND=""
GUM_LOG_KEY_FOREGROUND="#008B8B" # Dark Cyan (ContrastSecondaryTextColor)
GUM_LOG_KEY_BACKGROUND=""
GUM_LOG_VALUE_FOREGROUND="#00FF00" # Green (TertiaryTextColor)
GUM_LOG_VALUE_BACKGROUND=""
GUM_LOG_SEPARATOR_FOREGROUND="#FFFFFF" # White (BorderColor)
GUM_LOG_SEPARATOR_BACKGROUND=""

# 256-Color Code Definitions for Log Levels
# 256-Color Code Definitions for Log Levels
LOG_START_COLOR="38;5;69"            # Blue (#579BD5)
LOG_TASK_COLOR="38;5;48"             # Green (#4EC9B0)
LOG_STEP_DETAIL_COLOR="38;5;140"     # Bright Purple (#975EAB)
LOG_STEP_LOG_OUTPUT_COLOR="38;5;242" # Bright Black (#797979)
LOG_STEP_COMMAND_COLOR="38;5;229"    # Bright Yellow (#e9ad95)
LOG_STEP_COLOR="38;5;96"             # Purple (#714896)
LOG_PASS_COLOR="38;5;48"             # Bright Green (#1AD69C)
LOG_FAIL_COLOR="38;5;197"            # Bright Red (#EB2A88)
LOG_SKIP_COLOR="38;5;244"            # Grey (#808080)
LOG_DONE_COLOR="38;5;44"             # Cyan (#00B6D6)
LOG_ERROR_COLOR="38;5;197"           # Red (#E92888)
LOG_WARN_COLOR="38;5;180"            # Yellow (#CE9178)
LOG_INFO_COLOR="38;5;75"             # Bright Blue (#9CDCFE)
LOG_DEBUG_COLOR="38;5;140"           # Bright Purple (#975EAB)
LOG_SUCCESS_COLOR="38;5;229"         # Bright Yellow (#e9ad95)
LOG_USAGE_COLOR="38;5;208"           # Orange (no direct match, keeping original)
LOG_NOTE_COLOR="38;5;140"            # Bright Purple (#975EAB)
LOG_RESULT_COLOR="38;5;44"           # Cyan (#00B6D6)
LOG_QUERY_COLOR="38;5;197"           # Bright Red (#EB2A88)
LOG_DEFAULT_COLOR="38;5;242"         # Bright Black (#797979)

# Exporting the variables if needed
# Export all icon and emoji variables
for var in $(set | grep -E '[A-Z]+(_COLOR|_ICON|_EMOJI)=' | cut -d= -f1); do
    [ -n "${var+x}" ] && export "${var?}"
done
for var in $(set | grep -E '^(CURSOR|TEXT|COLOR|GUM|LOG|TEXT)_' | cut -d= -f1); do
    [ -n "${var+x}" ] && export "${var?}"
done

# ===============================
# Environment Handling
# ===============================

# Handle Non-TTY Environments
if [ -z "${CI+x}" ] && [ ! -t 1 ]; then
    COLOR_RED=''
    COLOR_GREEN=''
    COLOR_YELLOW=''
    COLOR_BLUE=''
    COLOR_MAGENTA=''
    COLOR_CYAN=''
    COLOR_WHITE=''
    NC=''
    COLOR_BOLD=''
    COLOR_BOLD_RED=''
    COLOR_BOLD_GREEN=''
    COLOR_BOLD_YELLOW=''
    COLOR_BOLD_BLUE=''
    COLOR_BOLD_MAGENTA=''
    COLOR_BOLD_CYAN=''
    COLOR_BOLD_WHITE=''
fi

# ===============================
# Utility Functions
# ===============================
# 🧰 Utility Functions for Logging and Formatting

## @fn command_exists
##
## @brief Check if a command exists in the system's PATH.
##
## @param $1 The command to check for existence.
##
## @return 0 if the command exists, 1 otherwise.
##
## @example
##   if command_exists git; then
##       echo "Git is installed"
##   fi
##
command_exists() {
    command -v "$@" >/dev/null 2>&1
}

# Wrapper function to prefer plum over gum for rich terminal output
# Priority order:
#   1. plum (if full shlocksmith repo is available) - fastest, most reliable
#   2. gum (if installed on system) - rich output when sourced remotely
#   3. return 1 (neither available) - functions fall back to basic formatting
# This allows log_functions.sh to be sourced remotely and still provide
# rich output if the user has gum installed, while preferring our optimized
# plum implementation when the full repo is available.
_gum() {
    if [ -n "${SHLOCKSMITH_PROJECT_BIN_DIR:-}" ] && [ -x "${SHLOCKSMITH_PROJECT_BIN_DIR}/plum" ]; then
        "${SHLOCKSMITH_PROJECT_BIN_DIR}/plum" "$@"
    elif command_exists gum; then
        gum "$@"
    else
        return 1
    fi
}

command_exists_validated() {
    cmd_path=$(command -v "$@" 2>/dev/null)
    case "${cmd_path}" in
        /* | ./* | ../*)
            if [ -f "${cmd_path}" ] && [ -x "${cmd_path}" ]; then
                return 0
            else
                return 1
            fi
            ;;
        *)
            # Not an external executable (could be a function, alias, or built-in)
            return 1
            ;;
    esac
}

## @fn short_sha256
##
## @brief Create a short SHA-256 hash from a given input string.
##
## @param $1 The input string to hash.
##
## @output Prints the first 8 characters of the SHA-256 hash.
##
## @example
##   short_sha256 "hello"
##   # Output: 2cf24dba
##
short_sha256() {
    printf "%s" "${1}" | sha256sum | awk '{print $1}' | cut -c1-8
}

## @fn pad_emoji
##
## @brief Pad an emoji with spaces to a specific width.
##
## @param $1 The emoji or string to pad.
## @param $2 The desired width in characters (including the emoji).
##
## @output Prints the emoji followed by the necessary spaces to fill the width.
##
## @example
##   pad_emoji "✅" 10
##   # Output: "✅        "
##
pad_emoji() {
    emoji="$1"                                    # The emoji or string to pad.
    width="$2"                                    # Desired width.
    emoji_width=$(printf "%b" "${emoji}" | wc -m) # Get the width of the emoji.
    padding=$((width - emoji_width + 1))          # Calculate the padding needed.
    printf "%s%*s" "${emoji}" "${padding}" " "    # Print the emoji with padding.
}

## @fn repeat_char
##
## @brief Repeat a character a specified number of times.
##
## @param $1 The character to repeat.
## @param $2 The number of times to repeat the character.
##
## @output Prints the character repeated the specified number of times, followed by a newline.
##
## @example
##   repeat_char "*" 5
##   # Output: *****
##
repeat_char() {
    printf "%0.s${1}" $(seq 1 "${2}")
    printf "\n" # Add a newline at the end.
}
## @fn horizontal_line
##
## @brief Create a horizontal line made up of a repeated character.
##
## @param $1 The desired width of the line.
## @param $2 (Optional) The character to repeat for the line. Defaults to "#".
##
## @output Prints a line of the repeated character, with a maximum length of 78 characters.
##
## @example
##   horizontal_line 50 "*"
##   # Output: **************************************************
##
horizontal_line() {
    repeat_char "${2:-"#"}" "$(min 78 "$1")"
}

## @fn embed_word
##
## @brief Embed a word within a string of padding.
##
## @param $1 The padding string that will surround the word.
## @param $2 The word to embed within the padding.
##
## @output Prints the word centered within the padding, or the word alone if it exceeds the padding length.
##
## @example
##   embed_word "************" "hello"
##   # Output: "***hello***"
##
embed_word() {
    padding="$1"
    word="$2"

    padding_length=${#padding}
    word_length=${#word}

    if [ "${word_length}" -ge "${padding_length}" ]; then
        printf "%s" "${word}"
        return
    fi

    total_padding=$((padding_length - word_length))
    left_padding=$((total_padding / 2))
    right_padding=$((total_padding - left_padding))

    left_part=$(echo "${padding}" | cut -c1-"${left_padding}")
    right_part=$(echo "${padding}" | cut -c1-"${right_padding}")

    printf "%s%s%s" "${left_part}" "${word}" "${right_part}"
}

## @fn stripcolor
##
## @brief Strip ANSI color codes from a string.
##
## @param $* The string with potential ANSI color codes.
##
## @output Prints the string with all ANSI color codes removed.
##
## @example
##   stripcolor "$(echo -e '\033[0;31mRed Text\033[0m')"
##   # Output: "Red Text"
##
stripcolor() {
    printf '%b' "$*" | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g'
}

## @fn get_printed_length
##
## @brief Get the printed length of a string, ignoring any color codes.
##
## @param $* The input string(s) whose printed length is to be calculated.
##
## @output Prints the length of the string without color codes.
##
## @example
##   get_printed_length "$(echo -e '\033[31mHello\033[0m')"
##   # Output: 5
##
# shellcheck disable=SC1087,SC2250
get_printed_length() {
    # Strip ANSI escape sequences using sed
    stripcolor "$*" | wc -m
}

## @fn to_stderr
##
## @brief Send output to stderr (standard error).
##
## @param $* (optional) The message to be sent to stderr. If not provided, reads from stdin.
##
## @output Prints the message or the stdin input to stderr.
##
## @example
##   echo "This is an error message" | to_stderr
##   to_stderr "Direct error message"
##
to_stderr() {
    if [ $# -eq 0 ]; then
        # No arguments, read from stdin and print each line to stderr
        while IFS= read -r line; do
            echo "${line}" >&2
        done
    else
        # If arguments are provided, print them to stderr
        echo "$*" >&2
    fi
}

# ===============================
# Logging Functions
# ===============================

# 🎉 Logging Functions to Add Sparkle to Your Scripts!

## @fn _shlocksmith__in_container
##
## @brief Detect if the script is running inside a Docker container.
##
## @details
## Checks for Docker-specific files and identifiers to determine
## whether the current environment is inside a container.
##
## @retval 0 if inside a Docker container, 1 otherwise.
##
_shlocksmith__in_container() {
    # Check if we're in a Docker container
    # Returns 0 (true) if in container, 1 (false) if not
    if test -e /.dockerenv; then
        return 0
    fi

    if grep -q docker /proc/1/cgroup 2>/dev/null; then
        return 0
    fi

    return 1
}

## @fn detect_color_support
##
## @brief Detect if the terminal supports color output.
##
## @details
## Checks various environment variables and terminal capabilities
## to determine if color output is supported.
##
## @retval 0 if color support is detected, 1 otherwise.
##
detect_color_support() {
    # Check for common environment variables indicating color support
    if [ -n "${COLORTERM+x}" ]; then
        # Color support detected (COLORTERM is set)
        return 0
    elif [ -n "${CLICOLOR+x}" ]; then
        # Color support detected (CLICOLOR is set)
        return 0
    elif [ -n "${TERM+x}" ] && [ "${TERM+x}" != "dumb" ]; then
        case "${TERM}" in
            xterm* | rxvt* | eterm* | screen* | tmux* | ansi | *color*)
                # Color support likely based on TERM variable
                return 0
                ;;
        esac
    fi

    # Check if stdout is a terminal
    if [ -t 1 ]; then
        # Try to print a color escape sequence and check if it's accepted
        if printf '\033[0m' >/dev/null 2>&1; then
            # Color support detected (escape sequence test passed)
            return 0
        fi
    fi

    # No color support detected
    return 1
}

## @fn _shlocksmith__auto_enable_colors
##
## @brief Automatically enable colors if the terminal supports it.
##
## @details
## Checks whether the output is being piped or running inside a
## continuous integration (CI) environment, and enables colors accordingly.
##
## @retval 0 if colors should be enabled, 1 otherwise.
##
_shlocksmith__auto_enable_colors() {
    test -z "${DOCKER_BUILD-}" && _shlocksmith__in_container && export DOCKER_BUILD=true
    if detect_color_support; then
        return 0
    elif command_exists tput && ! tput setaf 1 >/dev/null 2>&1 && ! tput AF 1 >/dev/null 2>&1; then
        return 1
    elif test -t 1 || [ -n "${CI-}" ] || [ -n "${GITLAB_CI-}" ] || [ -n "${DOCKER_BUILD-}" ]; then
        # Stdout is a terminal or CI environment
        return 0
    else
        return 1
    fi
}

## @fn _shlocksmith__enable_colors
##
## @brief Enable or disable terminal colors based on user settings.
##
## @details
## Allows for forced enabling, disabling, or auto-detection of terminal colors.
## Controlled by the `SHLOCKSMITH_PROJECT_ENABLE_TERMINAL_COLOR` environment variable.
##
## @output Echoes "true" if colors are enabled, "false" otherwise.
##
## @retval 0 Always returns 0 after echoing the result.
##
_shlocksmith__enable_colors() {
    _shlocksmith_color_choice="$(echo "${SHLOCKSMITH_PROJECT_ENABLE_TERMINAL_COLOR:-auto}" | tr '[:upper:]' '[:lower:]')"

    case "${_shlocksmith_color_choice}" in
        on | true | 1)
            echo "true"
            return 0
            ;;
        off | false | 0)
            echo "false"
            return 0
            ;;
        *)
            _shlocksmith__auto_enable_colors && echo "true" && return 0
            echo "false"
            ;;
    esac
}

## @fn _shlocksmith__colors_enabled
##
## @brief Check if colors are enabled for terminal output.
##
## @details
## Calls _shlocksmith__enable_colors and returns its result,
## effectively determining whether colors should be used in the terminal output.
##
## @retval 0 if colors are enabled, 1 otherwise.
##
_shlocksmith__colors_enabled() {
    "$(_shlocksmith__enable_colors)"
}

## @fn colorize
##
## @brief Wrap a message in color codes for terminal output.
##
## @param $1 The color code or variable name representing the color code.
## @param $* The message to be printed with the color applied.
##
## @output Prints the message with the color code applied if colors are enabled, or without color if disabled.
##
## @example
##   colorize COLOR_BOLD_RED "This is an error message"
##   colorize COLOR_GREEN "Success"
##
colorize() {
    if ! _shlocksmith__colors_enabled; then
        shift
        printf "%b\n" "$*"
    else
        color_code="$1"

        if echo "${color_code}" | grep -q -E '^[A-Z_]+'; then
            eval "color_code=\"\${${color_code}}\""
        fi

        shift
        message="$*"
        message="${message%"${NC}"}"

        printf "%b%b%b\n" "${color_code}" "${message#"${color_code}"}" "${NC}"
    fi
}

## @brief Calculate the display width of a string, ignoring ANSI color codes.
## @param $1 The text to measure.
## @retval The number of printable characters in the string.
##
get_print_width() {
    get_printed_length "$*"

    # text="$1"
    # # Remove ANSI escape sequences
    # stripped=$(printf "%s" "${text}" | sed "s/\x1B\[[0-9;]*[JKmsu]//g")
    # # Count the number of printable characters
    # printf "%s" "${stripped}" | wc -m
}

get_longest_key_length() {
    max_length=0
    while test $# -gt 0; do
        key="$1"
        shift
        if [ $# -gt 0 ]; then
            shift
        fi
        key_length=$(get_printed_length "${key}")
        if [ "${key_length}" -gt "${max_length}" ]; then
            max_length="${key_length}"
        fi
    done
    printf "%d" "${max_length}"
}

colorize_key_value_pairs() {
    max_key_length=$(get_longest_key_length "$@")
    while test $# -gt 0; do
        key="$1"
        shift
        if [ $# -gt 0 ]; then
            value="$1"
            shift
        else
            value="missing value"
        fi
        key_length=$(get_printed_length "${key}")
        padding=$((2 + max_key_length - key_length))
        printf '%b%b%b%*s %b%b%b\n' \
            "${COLOR_RESET-}${LOG_KEY_FOREGROUND-}${LOG_KEY_BACKGROUND-}" \
            "${key}" \
            "${COLOR_RESET-}${LOG_SEPARATOR_FOREGROUND-}${LOG_SEPARATOR_BACKGROUND-}" \
            "${padding}" ":" \
            "${LOG_VALUE_FOREGROUND-}${LOG_VALUE_BACKGROUND-}" \
            "${value}" \
            "${COLOR_RESET-}"
    done
}

print_from_to() {
    from="$1"
    to="$2"
    colorize_key_value_pairs "From" "${from}" "To" "${to}"
}

## @brief Add indentation to multi-line text output.
## @param $1 The number of spaces for indentation.
## @param $2 The text to be indented.
## @param $3 An optional prefix to include before the indent.
## @details
## Indents all lines of the input text except the first one. If colors are enabled, the text will be reset with `COLOR_RESET`.
##
_shlocksmith__indent_text() {
    indent_size="$1"
    text="$2"
    prefix="$3"
    nl='
'
    # Create the indent string for subsequent lines
    indent=$(printf '%*s' "${indent_size}" '')

    # Process the text: handle the first line separately (no indent), then indent subsequent lines
    printf '%b%b' "${prefix}" "${text}" | sed "1n;s/^/${indent}/"
}

rfc3339_date() {
    if date --rfc-3339=seconds >/dev/null 2>&1; then
        date --rfc-3339=seconds
    else
        date "+%Y-%m-%d %H:%M:%S%:z"
    fi
}

print_log_message() {

    log_level="${1}"
    shift
    log_prefix="${1}"
    shift
    inside_of_step="${1}"
    shift
    this_log_message="${1}"
    shift
    log_display_timestamp=true
    if [ -n "${FF_TIMESTAMPS-}" ] || [ "${FF_TIMESTAMPS-0}" -eq "1" ]; then
        unset log_display_timestamp
    fi

    dim_prefix=""
    if [ "${inside_step:-false}" = "true" ]; then
        dim_prefix="$(printf '\033[2m')" # Dim text
    fi

    case "${log_level}" in
        START*) color="$(printf '\033[%sm' "${LOG_START_COLOR}")" ;;
        TASK*) color="$(printf '\033[%sm' "${LOG_TASK_COLOR}")" ;;
        DETAIL*) color="$(printf '\033[%sm' "${LOG_STEP_DETAIL_COLOR}")" ;;
        RUNCMD*) color="$(printf '\033[%sm' "${LOG_STEP_COMMAND_COLOR}")" ;;
        OUTPUT*) color="$(printf '\033[%sm' "${LOG_STEP_LOG_OUTPUT_COLOR}")" ;;
        STEP*) color="$(printf '\033[%sm' "${LOG_STEP_COLOR}")" ;;       # Bright Magenta (256-color)
        PASS*) color="$(printf '\033[%sm' "${LOG_PASS_COLOR}")" ;;       # Bold Green (256-color)
        FAIL*) color="$(printf '\033[%sm' "${LOG_FAIL_COLOR}")" ;;       # Bold Red (256-color)
        SKIP*) color="$(printf '\033[%sm' "${LOG_SKIP_COLOR}")" ;;       # Grey(256-color)
        DONE*) color="$(printf '\033[%sm' "${LOG_DONE_COLOR}")" ;;       # Bold Green (256-color)
        ERROR*) color="$(printf '\033[%sm' "${LOG_ERROR_COLOR}")" ;;     # Bold Red (256-color)
        WARN*) color="$(printf '\033[%sm' "${LOG_WARN_COLOR}")" ;;       # Bold Yellow (256-color)
        INFO*) color="$(printf '\033[%sm' "${LOG_INFO_COLOR}")" ;;       # White (Reset)
        DEBUG*) color="$(printf '\033[%sm' "${LOG_DEBUG_COLOR}")" ;;     # Bold Blue (256-color)
        SUCCESS*) color="$(printf '\033[%sm' "${LOG_SUCCESS_COLOR}")" ;; # Bold Green (256-color)
        USAGE*) color="$(printf '\033[%sm' "${LOG_USAGE_COLOR}")" ;;     # Bright Yellow (256-color)
        NOTE*) color="$(printf '\033[%sm' "${LOG_NOTE_COLOR}")" ;;       # Bright Magenta (256-color)
        RESULT*) color="$(printf '\033[%sm' "${LOG_RESULT_COLOR}")" ;;   # Bright Cyan (256-color)
        QUERY*) color="$(printf '\033[%sm' "${LOG_QUERY_COLOR}")" ;;     # Bright Green (256-color)
        *) color="$(printf '\033[%sm' "${LOG_DEFAULT_COLOR}")" ;;        # Default Grey (256-color)
    esac

    indent_width=0
    long_prefix_string=""
    if [ -n "${log_display_timestamp+x}" ]; then
        date_str="$(rfc3339_date)"
        indent_width=$((${#date_str} + 1))
        long_prefix_string="${long_prefix_string}$(printf "%s " "$(colorize "${COLOR_GREY}" "${date_str}")")"
    fi

    if [ -n "${log_level+x}" ]; then
        printed_len="$(get_printed_length "${log_level}")"
        indent_width=$((printed_len + indent_width + 1))
        long_prefix_string="${long_prefix_string}$(printf "%s " "$(colorize "${color}" "${log_level}")")"
    fi

    if [ -n "${log_prefix+x}" ]; then
        printed_len="$(get_printed_length "${log_prefix}")"
        indent_width=$((printed_len + indent_width + 1))
        long_prefix_string="${long_prefix_string}$(printf "%b " "$(colorize "${COLOR_BRIGHT_YELLOW}" "${log_prefix}")")"
    fi
    _shlocksmith__indent_text "${indent_width}" "${this_log_message-}" "${long_prefix_string}"
    if [ $# -gt 0 ] && [ -n "$*" ]; then
        colorize_key_value_pairs "$@" | while IFS= read -r line; do
            printf "\n%s %b  %b" "$(horizontal_line "${indent_width}" " ")" "${HIDDEN_CIRCLE_ICON}" "${line}"
        done
    fi
    printf "\n"

}

## @fn log_message
##
## @brief Log a message with a specific type, timestamp, and optional emoji.
##
## @param $1 The type of log message (e.g., INFO, ERROR, DEBUG).
## @param $2 The message to be logged.
## @param $3 (Optional) Emoji to prefix the message.
##
## @output Prints a formatted log message to stdout.
##
## @details
## This function formats log messages with a consistent structure, including
## message type, timestamp (if enabled), and an optional emoji. It handles
## multiline messages by logging each line separately with proper formatting.
##
## @example
##   log_message "INFO" "Process started" "✅"
##   log_message "ERROR" "Failed to connect to server" "❌"
##
log_message() {
    # Requires at least 5 arguments: log_level, prefix, inside_of_step, emoji, message
    [ $# -lt 5 ] && return 0
    log_level="$(printf "%-7s" "${1:-}" | tr '[:lower:]' '[:upper:]')"
    shift || :
    log_prefix="${1:-}"
    shift || :
    inside_of_step="${1:-}"
    shift || :
    emoji="${1:-}"
    shift || :
    message="${1:-}"
    shift || :
    # Add padding to emoji if provided
    padded_emoji="$(printf "%b" "$(pad_emoji "${emoji}" 3)")"

    print_log_message "${log_level}" "${padded_emoji}${prefix}" "${inside_of_step}" "${message}" "${@}"

}
## @fn log_start
##
## @brief Log the start of a process or operation.
##
## @param $* The message describing the process or operation starting.
##
## @output Prints a formatted "START" log message.
##
## @example
##   log_start "Initializing database connection"
##
log_start() {
    prefix=""
    log_message "START" "${prefix}" "false" "${START_ICON-}" "$@"
}
log_starting() {
    log_start "$@"
}

## @fn log_step_start
##
## @brief Log the start of a step within a process.
##
## @param $* The message describing the step starting.
##
## @output Prints a formatted "TASK" log message.
##
## @example
##   log_step_start "Validating user input"
##
log_step_start() {
    prefix="> "
    log_message "TASK" "${prefix}" "true" "${STEP_START_ICON-}" "$@"
}

log_step_detail() {
    prefix="  "
    log_message "DETAIL" "${prefix}" "true" "${STEP_INFO_ICON-}" "$@"
}
log_step_details() { log_step_detail "$@"; }
log_step_info() { log_step_detail "$@"; }

log_step_command() {
    prefix="  "
    log_message "RUNCMD" "${prefix}" "true" "${STEP_LOG_COMMAND_ICON-}" "$@"
}
log_step_log_output() {
    prefix="  "
    log_message "OUTPUT" "${prefix}" "true" "${STEP_LOG_OUTPUT_ICON-}" "$@"
}

## @fn log_step
##
## @brief Log a step within a process.
##
## @param $* The message describing the step.
##
## @output Prints a formatted "STEP" log message.
##
## @example
##   log_step "Processing file: example.txt"
##
log_step() {
    prefix="   ◇◇ "
    log_message "STEP" "${prefix}" "true" "${CIRCLE_BULLET_ICON-}" "$@"
}

## @fn log_step_pass
##
## @brief Log a successful step completion.
##
## @param $* The message describing the successful step.
##
## @output Prints a formatted "PASS" log message.
##
## @example
##   log_step_pass "User authentication successful"
##
log_step_pass() {
    prefix="    - "
    log_message "PASS" "${prefix}" "true" "${PASS_ICON-}" "$@"
}
log_step_success() {
    log_step_pass "$@"
}

## @fn log_step_failed
##
## @brief Log a failed step.
##
## @param $* The message describing the failed step.
##
## @output Prints a formatted "FAIL" log message.
##
## @example
##   log_step_failed "Database connection failed"
##
log_step_failed() {
    prefix="    - "
    log_message "FAIL" "${prefix}" "true" "${FAIL_EMOJI-}" "$@"
}
log_step_failure() {
    log_step_failed "$@"
}
log_step_fail() {
    log_step_failed "$@"
}

log_step_skipped() {
    prefix="    - "
    log_message "SKIP" "${prefix}" "true" "${SKIP_ICON-}" "$@"
}
log_step_skip() {
    log_step_skipped "$@"
}

## @fn log_step_done
##
## @brief Log the completion of a step or process.
##
## @param $* The message describing the completed step or process.
##
## @output Prints a formatted "DONE" log message.
##
## @example
##   log_step_done "Configuration update completed"
##
log_step_done() {
    prefix="  "
    log_message "DONE" "${prefix}" "true" "${STEP_DONE_ICON-}" "$@"
}

## @fn log_error
##
## @brief Log an error message.
##
## @param $* The error message to be logged.
##
## @output Prints a formatted "ERROR" log message to stderr.
##
## @example
##   log_error "Failed to write to log file"
##
log_error() {
    prefix=""
    log_message "ERROR" "${prefix}" "false" "${ERROR_EMOJI}" "$@" | to_stderr
}

## @fn log_fatal
##
## @brief Log a fatal error message and exit the script.
##
## @param $* The fatal error message to be logged.
##
## @output Prints a formatted "ERROR" log message with "FATAL:" prefix to stderr and exits.
##
## @example
##   log_fatal "Critical system failure, shutting down"
##
log_fatal() {
    return_code=$?
    [ $# -eq 0 ] && return 0
    [ "${return_code:-0}" -eq 0 ] && return_code=1
    log_message "ERROR" "false" " FATAL" "${FATAL_ICON-}" "$@" | to_stderr
    exit "${return_code}"
}
log_abort() {
    log_fatal "$@"
}

## @fn log_warning
##
## @brief Log a warning message.
##
## @param $* The warning message to be logged.
##
## @output Prints a formatted "WARN" log message to stderr.
##
## @example
##   log_warning "Low disk space detected"
##
log_warning() {
    prefix=""
    log_message "WARN" "${prefix}" "false" "${WARNING_EMOJI}" "$@" | to_stderr
}
log_warn() {
    log_warning "$@"
}

## @fn log_info
##
## @brief Log an informational message.
##
## @param $* The informational message to be logged.
##
## @output Prints a formatted "INFO" log message.
##
## @example
##   log_info "System status: OK"
##
log_info() {
    prefix=""
    log_message "INFO" "${prefix}" "false" "${INFO_EMOJI}" "$@"
}

## @fn log_debug
##
## @brief Log a debug message if debugging is enabled.
##
## @param $* The debug message to be logged.
##
## @output Prints a formatted "DEBUG" log message if DEBUG is set and not false.
##
## @example
##   log_debug "Variable x = 5"
##
log_debug() {
    prefix=""
    if [ -n "${DEBUG+x}" ] && echo "${DEBUG}" | grep -vqE '^(false|False|FALSE|No|no|NO|0)'; then
        log_message "DEBUG" "${prefix}" "false" "${INFO_EMOJI}" "$@"
    fi
}

## @fn log_usage
##
## @brief Log a usage message.
##
## @param $* The usage message to be logged.
##
## @output Prints a formatted "USAGE" log message.
##
## @example
##   log_usage "script.sh [OPTIONS]"
##
log_usage() {
    prefix=""
    log_message "USAGE" "${prefix}" "false" "${USAGE_EMOJI}" "$@"
}

## @fn log_notice
##
## @brief Log a notice message.
##
## @param $* The notice message to be logged.
##
## @output Prints a formatted "NOTE" log message.
##
## @example
##   log_notice "Scheduled maintenance in 24 hours"
##
log_notice() {
    prefix=""
    log_message "NOTE" "${prefix}" "false" "${NOTICE_EMOJI}" "$@"
}
log_note() {
    log_notice "$@"
}

## @fn log_done
##
## @brief Log a completion message.
##
## @param $* The completion message to be logged.
##
## @output Prints a formatted "DONE" log message.
##
## @example
##   log_done "Backup process completed successfully"
##
log_done() {
    prefix=""
    log_message "DONE" "${prefix}" "false" "${DONE_EMOJI}" "$@"
}
log_finished() {
    log_done "$@"
}

## @fn log_result
##
## @brief Log a result message.
##
## @param $* The result message to be logged.
##
## @output Prints a formatted "RESULT" log message.
##
## @example
##   log_result "Test suite: 95% pass rate"
##
log_result() {
    prefix=""
    log_message "RESULT" "${prefix}" "false" "${RESULTS_ICON}" "$@"
}

## @fn log_query
##
## @brief Log a query or question.
##
## @param $* The query or question to be logged.
##
## @output Prints a formatted "QUERY" log message.
##
## @example
##   log_query "User input required: Enter username"
##
log_query() {
    prefix=""
    log_message "QUERY" "${prefix}" "false" "${QUESTION_ICON}" "$@"
}
log_question() {
    log_query "$@"
}

## @fn log_pass
##
## @brief Log a pass message.
##
## @param $* The pass message to be logged.
##
## @output Prints a formatted "PASS" log message.
##
## @example
##   log_pass "All tests passed successfully"
##
log_pass() {
    prefix=""
    log_message "PASS" "${prefix}" "false" "${PASS_ICON}" "$@"
}

## @fn log_success
##
## @brief Log a success message.
##
## @param $* The success message to be logged.
##
## @output Prints a formatted "SUCCESS" log message.
##
## @example
##   log_success "Deployment completed successfully"
##
log_success() {
    prefix=""
    log_message "SUCCESS" "${prefix}" "false" "${SUCCESS_ICON}" "$@"
}

## @fn log_failure
##
## @brief Log a failure message.
##
## @param $* The failure message to be logged.
##
## @output Prints a formatted "FAIL" log message.
##
## @example
##   log_failure "Build process failed"
##
log_failed() {
    prefix=""
    log_message "FAIL" "${prefix}" "false" "${FAIL_EMOJI}" "$@"
}
log_failure() {
    log_failed "$@"
}
log_fail() {
    log_failed "$@"
}

# Checks if the input string contains only non-printing characters.
# It uses `printf` to interpret escape sequences and `sed` to remove ANSI escape codes and trim whitespace.
# Returns true (0) if the string is empty or contains only non-printing characters, false (1) otherwise.
string_is_non_printing() {
    [ -z "$(printf "%b" "${*}" | sed -e 's/\x1B\[[0-9;]*[JKmsu]//g' -e 's/^[ \t]*//;s/[ \t]*$//')" ]
}
if ! command_exists trim; then
    trim() {
        printf "%b" "${*}" | sed -e 's/^[ \t]*//;s/[ \t]*$//'
    }
fi
highlight_with() {
    highlight_color="$1"
    input_string="$2"

    # Use sed to replace ANSI reset codes (\033[0m) with the highlight color
    # and prepend the highlight color to the start of the string
    modified_string="$(printf "%b" "${input_string}" | sed "s/\x1B\[0m/${highlight_color}/g")"

    # Prepend the highlight color to the start of the string
    printf "%b%s%b" "${highlight_color}" "${modified_string}" "${COLOR_RESET:-}"
}
task_output() {
    return_code="$1"
    shift
    if ! string_is_non_printing "$*"; then

        raw_task_output=$(trim "${*:-}")
        highlight_color="${LOG_BLOCK_TEXT_FOREGROUND:-}"
        if [ -n "${highlight_color}" ]; then
            highlighted_log=$(highlight_with "${highlight_color}" "${raw_task_output}")
            printf "\n%b%b%b\n" "${COLOR_ITALIC}" "${highlighted_log}" "${COLOR_RESET:-}"
        else
            printf "\n%b\n" "${raw_task_output}"
        fi
    fi

}
log_execute_task() {
    task_description="$1"
    shift
    command_to_run="$*"
    if task_output="$("$@" 2>&1)"; then
        return_code="0"
    else
        return_code="1"
    fi
    if [ -n "${task_output:-}" ]; then
        log_step_log_output "$(task_output "${return_code}" "${task_output}")"
    fi
    if [ "${return_code}" -eq 0 ]; then
        log_step_pass "Complete: ${task_description}"
    else
        log_step_failed "Failed  : ${task_description}"
        return 1
    fi
}

do_step_task_inline() {
    task_description="${1:-}"
    shift
    log_execute_task "${task_description:-}" "${@}"
}

do_step_task() (
    task_description="$1"
    shift
    command_to_run="$*"
    log_step_start "${task_description:-}"
    log_step_command "${LOG_KEY_FOREGROUND:-}${COLOR_ITALIC:-}${command_to_run:-}${COLOR_ITALIC_END:-}${COLOR_RESET:-}"
    log_execute_task "${task_description:-}" "${@}"
)

# Helper functions for logging
## @fn min
##
## @brief Returns the minimum of two numbers.
##
## @param $1 The first number to compare.
## @param $2 The second number to compare.
##
## @output Prints the smaller of the two input numbers.
##
## @example
##   min 5 3
##   Output: 3
##
min() {
    if [ "$1" -le "$2" ]; then
        echo "$1"
    else
        echo "$2"
    fi
}

## @fn max
##
## @brief Returns the maximum of two numbers.
##
## @param $1 The first number to compare.
## @param $2 The second number to compare.
##
## @output Prints the larger of the two input numbers.
##
## @example
##   max 5 3
##   Output: 5
##
max() {
    if [ "$1" -ge "$2" ]; then
        echo "$1"
    else
        echo "$2"
    fi
}

if ! command_exists run_as_root; then

    run_as_root() {
        user="$(id -un 2>/dev/null || true)"

        if [ "${user}" != 'root' ]; then
            if command_exists sudo; then
                sh_c='sudo'
            else
                cat >&2 <<-'EOF'
					Error: this command needs the ability to run other commands as root.
					We are unable to find "sudo" available to make this happen.
				EOF
                exit 1
            fi
        fi
        ${sh_c-} "${@}"
    }
fi

# Install Gum
install_gum() {
    if [ -r /etc/os-release ]; then
        lsb_dist="$(. /etc/os-release && echo "${ID-}" | tr '[:upper:]' '[:lower:]')"
    fi
    case "${lsb_dist-}" in
        ubuntu | debian | raspbian)
            run_as_root apt-get -qq update || true
            run_as_root apt-get install -y -qq bash gnupg curl sudo ca-certificates
            curl -fsSL https://repo.charm.sh/apt/gpg.key | run_as_root gpg --dearmor -o /etc/apt/keyrings/charm.gpg || true
            echo 'deb [trusted=yes] https://repo.charm.sh/apt/ /' | run_as_root tee /etc/apt/sources.list.d/charm.list
            run_as_root apt-get -qq update || true
            run_as_root apt-get install -y -qq gum || log_failure "gum failed the install"
            ;;
        *)
            log_info "No gum installation instructions for this linux distribution - ${lsb_dist}"
            ;;
    esac
}

# ===============================
# Section Handling Functions
# ===============================

# ⚡ Functions for Managing Log Sections

## @fn section_start
##
## @brief Starts a collapsible section in GitLab CI logs or a visually distinct section in non-CI environments.
##
## @details
## In GitLab CI, this function creates a collapsible section in the job logs,
## allowing for better organization and easier navigation of log output.
## In non-CI environments, it prints a visually distinct header to clearly
## mark the beginning of a new section in the output.
##
## @param $1 (Optional) Unique key for the section (default: unlabeled_section).
## @param $2 (Optional) Header text for the section (default: section_key).
##
## @output Prints a formatted section start header.
##
## @example
##   section_start "build_phase" "Starting Build Process"
##
section_start() {
    section_key="${1:-unlabeled_section}"
    section_header="${2:-${section_key}}"
    collapsed="${3:-true}"
    if [ -n "${GITLAB_CI+x}" ]; then
        # GitLab CI-specific section start with collapsible header
        printf "\e[0Ksection_start:%s:%s[collapsed=%s]\r\e[0K%b%b\n" "$(date +%s)" "${section_key}" "${collapsed}" "${SECTION_EMOJI:+"${SECTION_EMOJI} "}" "${section_header}"
    else
        non_ci_section_start "${section_header}" "${section_key}"
    fi
}

## @fn section_end
##
## @brief Ends a collapsible section in GitLab CI logs or marks the end of a section in non-CI environments.
##
## @details
## In GitLab CI, this function marks the end of a collapsible section in the job logs.
## In non-CI environments, it prints a visually distinct footer to clearly
## mark the end of a section in the output.
##
## @param $1 (Optional) Unique key for the section (default: unlabeled_section).
##
## @output Prints a formatted section end marker or footer.
##
## @example
##   section_end "build_phase"
##
section_end() {
    section_key="${1:-unlabeled_section}"
    section_header="${2:-${section_key}}"
    if [ -n "${GITLAB_CI+x}" ]; then
        printf "\e[0Ksection_end:%s:%s\r\e[0K" "$(date +%s)" "${section_key}"
    else
        non_ci_section_end "${section_key}" "${section_header}"
    fi
}
color256() {
    color_code="$1"
    printf "\033[38;5;%bm" "${color_code}"
}
## @fn non_ci_section_start
##
## @brief Prints a styled section header for non-CI environments.
##
## @details
## This function creates a visually distinct header to mark the beginning of a
## section in non-CI environments. It uses color formatting and optional emoji
## to make the section start easily identifiable in the output.
##
## @param $1 The header text to be printed.
##
## @output Prints a formatted, colorized section header.
##
## @example
##   non_ci_section_start "Configuration Setup"
##
non_ci_section_start() {
    TITLE_COLOR_NUMBER=63
    SUBTITLE_COLOR_NUMBER=240
    BORDER_FOREGROUND=212
    section_key="${1:-unlabeled_section}"
    section_header="${2:-${section_key}}"
    title_length="$(get_printed_length "${section_header-}")"
    if [ -z "${SHLOCKSMITH_PROJECT__DISABLE_GUM+x}" ] && { [ -n "${SHLOCKSMITH_PROJECT_BIN_DIR:-}" ] && [ -x "${SHLOCKSMITH_PROJECT_BIN_DIR}/plum" ] || command_exists gum; }; then
        section_key_id="$(short_sha256 "${section_key}")"
        colored_section_key="$(_gum format -t template -- "{{ Color \"${SUBTITLE_COLOR_NUMBER}\" \"0\"  (Italic \"Starting section id ${section_key_id}\") }}")"
        _gum style \
            --foreground="${TITLE_COLOR_NUMBER}" --border-foreground="${BORDER_FOREGROUND}" --bold --border-background="0" --background="0" --border=double \
            --align=center --width="70" --margin="1 1" --padding="1 1" \
            "$(printf "%s\n%b" "${section_header}" "${colored_section_key}")"
    else
        line_width="$(max 70 "$(get_printed_length "${section_header-}")")"
        header_line="$(horizontal_line "${line_width}" "#")"
        middle_line="$(horizontal_line "$((line_width - 2))" " ")"
        printf "\n%b\n" "$(colorize "$(color256 "${BORDER_FOREGROUND}")" "${header_line}")"
        printf "%b" "$(colorize "$(color256 "${BORDER_FOREGROUND}")" "#${middle_line}#\n#")"
        printf "%b" "$(colorize "${COLOR_BOLD}$(color256 "${TITLE_COLOR_NUMBER}")" "$(embed_word "${middle_line}" "${section_header}")")"
        printf "%b\n" "$(colorize "$(color256 "${BORDER_FOREGROUND}")" "#\n#${middle_line}#")"
        printf "%b\n" "$(colorize "$(color256 "${BORDER_FOREGROUND}")" "${header_line}")"
    fi
}

## @fn non_ci_section_end
##
## @brief Prints a styled section footer for non-CI environments.
##
## @details
## This function creates a visually distinct footer to mark the end of a
## section in non-CI environments. It uses color formatting and optional emoji
## to make the section end easily identifiable in the output.
##
## @param $1 The header text of the section being closed.
##
## @output Prints a formatted, colorized section footer.
##
## @example
##   non_ci_section_end "Configuration Setup"
##
non_ci_section_end() {
    section_key="${1:-unlabeled_section}"
    section_header="${2:-${section_key}}"
    title_length=$(get_printed_length "${section_header-}")
    if [ -z "${SHLOCKSMITH_PROJECT__DISABLE_GUM+x}" ] && { [ -n "${SHLOCKSMITH_PROJECT_BIN_DIR:-}" ] && [ -x "${SHLOCKSMITH_PROJECT_BIN_DIR}/plum" ] || command_exists gum; }; then
        section_key_id="$(short_sha256 "${section_key}")"
        colored_section_key="$(_gum format -t template -- "{{ Color \"240\" \"0\"  (Italic \"Completed section id ${section_key_id}\") }}")"
        _gum style \
            --foreground="63" --border-foreground="212" --bold --border-background="0" --background="0" --border=double \
            --align=center --width="70" --margin="1 1" --padding="1 1" \
            "$(printf "%b\n%b" "${section_header}" "${colored_section_key}")"
    else
        line_width="$(max 70 "$(get_printed_length "${section_header-}")")"
        header_line="$(colorize "${COLOR_BRIGHT_MAGENTA}" "$(horizontal_line "${line_width}" "#")")"
        printf "%s\n\n" "${header_line}"
    fi
}

# ===============================
# Additional Combined Functions
# ===============================

# 🚀 Functions Combining Utilities and Logging

## @fn run_command_in_section
##
## @brief Runs a command inside a collapsible section with a start and end marker.
##
## @details
## Creates a section using the hash of the command, runs the command,
## and closes the section. Useful for organizing command output in logs.
##
## @param $@ The command to be executed and its arguments.
##
## @output Executes the command within a log section.
##
## @return The exit status of the executed command.
##
## @example
##   run_command_in_section make build
##
run_command_in_section() {
    # Generate a short SHA-256 hash of the command string
    sha=$(short_sha256 "$*")

    # Start the section with the generated hash as the section key
    section_start "${sha}" "$*"

    # Initialize a variable to track command failure
    failed=0

    # Run the command passed to the function
    "$@" || failed=1

    # End the section using the same hash
    section_end "${sha}"

    # Return the failure status (0 if successful, 1 if failed)
    return "${failed}"
}

## @fn print_single_log_file
##
## @brief Logs the contents of a specified file within a section.
##
## @details
## This function creates a section for a log file, prints its contents,
## and closes the section. It's useful for displaying log file contents
## in a structured and organized manner, especially in CI/CD output.
##
## @param $1 The path to the log file to be printed.
##
## @output Creates a section and prints the log file contents within it.
##
## @example
##   print_single_log_file "/path/to/logfile.log"
##
print_single_log_file() {
    # Get the log file path from the first argument
    log_file_path="$1"

    # Check if the file exists
    if [ -f "${log_file_path}" ]; then
        # Get the directory name for use in the section title
        short_filename="$(dirname "${log_file_path}")"

        # Start a new section for logging the file contents
        section_start "📄 ${short_filename}"

        # Log the file contents
        log_info "Log file contents: ${log_file_path}\n$(cat "${log_file_path}")"

        # End the section
        section_end "📄 ${short_filename}"
    fi
}

## @fn log_file_contents
##
## @brief Logs the contents of files matching a specified path pattern.
##
## @details
## This function searches for files matching the provided path pattern and logs
## their contents using print_single_log_file. It's useful for displaying multiple
## log files in a structured manner, especially in CI/CD environments.
##
## @param $* The path pattern of the log file(s) to be printed.
##
## @output Prints the contents of matching log files within sections.
##
## @example
##   log_file_contents "/var/log/app/*.log"
##
log_file_contents() (
    # Disable debugging and error tracing temporarily for this function
    set +x +e

    # Clean up the file path by collapsing repeated slashes
    log_file_path="$(printf "%s" "$*" | tr -s '/')"

    # Extract the directory from the log file path
    logdir="$(dirname "${log_file_path}")"

    # Check if the directory exists
    if [ -d "${logdir}" ]; then
        # Find files in the directory that match the base name of the log file path and process them
        find "${logdir}" -type f -iname "$(basename "${log_file_path}")" |
            while IFS= read -r file; do
                print_single_log_file "${file}"
            done
    fi

    # Always return 0, indicating success
    return 0
)

demonstrate_logging_function_styles() {
    log_start "Starting logging demonstration"
    log_step_start "Initializing demonstration"
    log_info "This is an informational message"
    log_debug "Debug information: x = 5, y = 10"
    log_warning "Warning: Disk space is running low"
    log_error "Error: Failed to connect to database"
    log_step "Processing data"
    log_step_pass "Data processing completed successfully"
    log_query "Do you want to continue? (y/n)"
    log_notice "Scheduled maintenance in 24 hours"
    log_result "Test suite: 95% pass rate"
    log_success "Deployment completed successfully"
    log_failure "Build process failed"
    log_step_done "Demonstration completed"
    log_done "Logging demonstration finished"
}

demonstrate_firmware_build_process() {
    log_start "Firmware Build Process"

    # Add section header for environment check
    section_start "env_check" ":mag: Environment Verification"
    log_step_start "Check environment"
    log_step_pass "CPU: Sufficient cores available"
    log_step_pass "RAM: Adequate memory detected"
    log_step_pass "Disk space: Sufficient free space"
    log_step_start "Verifying tool versions"
    log_step_pass "GCC version: 9.3.0"
    log_step_done "Environment ready"
    log_step_detail "Ensure all required tools are installed and up-to-date."
    log_step "CMake version 3.18.0 detected. Recommended: 3.20.0 or higher"
    section_end "env_check"

    # Add section header for dependency installation
    section_start "deps" ":package: Dependency Installation"
    log_step_start "Updating package lists"
    log_step_command "sudo apt-get update"
    log_step_pass "Package lists updated successfully"
    log_step_start "Installing required packages"
    log_step_command "sudo apt-get install build-essential cross-compilation-tools libusb-dev"
    log_step "600 packages to install"
    log_step_pass "Build essentials installed"
    log_step_pass "Cross-compilation tools installed"
    log_step_failed "Failed to install libusb-dev. Retrying..."
    log_step_command "sudo apt-get install libusb-dev"
    log_step_pass "libusb-dev installed successfully on second attempt"
    log_step_done "Dependency management completed"
    section_end "deps"

    # Add section header for source preparation
    section_start "source_prep" ":file_folder: Source Code Preparation"
    log_step_start "Preparing source code"
    log_step_start "Cloning firmware repository"
    log_step_command "git clone https://github.com/example/firmware.git"
    log_step_pass "Repository cloned successfully"
    log_step_start "Checking out release branch"
    log_step_command "git checkout release-v2.1"
    log_step_pass "Switched to branch 'release-v2.1'"
    log_step_start "Applying patches"
    log_step_detail "Applying necessary patches to the source code."
    log_step "45 patches to apply"
    log_step_pass "Patch 001: Applied successfully"
    log_step_pass "Patch 002: Applied successfully"
    log_step_failed "Patch 003: Failed to apply. Skipping patch 003. Manual intervention may be required."
    log_step_done "Source code setup completed"
    section_end "source_prep"

    # Add section header for build process
    section_start "build" ":hammer: Building Firmware"
    log_step_start "Building firmware"
    log_step_start "Generating build files"
    log_step_command "cmake .."
    log_step_pass "CMake configuration completed"
    log_step_start "Compiling source files"
    log_step_command "make -j$(nproc)"
    log_step_log_output "Compiling output:
[ 10%] Building C object CMakeFiles/firmware.dir/src/main.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/src/utils.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/src/init.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/src/driver.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/src/hardware.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/src/network.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/src/security.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/src/storage.c.o
[ 90%] Building C object CMakeFiles/firmware.dir/src/update.c.o
[100%] Linking C executable firmware"
    log_step_pass "Compilation completed successfully"
    log_step_start "Linking objects"
    log_step_command "make link"
    log_step_pass "Linking completed"
    log_step_start "Generating firmware binary"
    log_step_command "make firmware"
    log_step_pass "Firmware binary created: firmware-v2.1.bin"
    log_step_done "Firmware build completed"
    section_end "build"

    # Add section header for OTA package generation
    section_start "ota" ":package: OTA Package Generation"
    log_step_start "Generating OTA files"
    log_step_start "Generating checksums"
    log_step_command "md5sum firmware-v2.1.bin > firmware-v2.1.md5"
    log_step_pass "MD5 checksum generated"
    log_step_command "sha256sum firmware-v2.1.bin > firmware-v2.1.sha256"
    log_step_pass "SHA256 checksum generated"
    log_step_start "Creating firmware package"
    log_step_command "zip firmware-v2.1.zip firmware-v2.1.bin firmware-v2.1.md5 firmware-v2.1.sha256"
    log_step_pass "Firmware package created: firmware-v2.1.zip"
    log_step_done "Firmware build processes completed"
    section_end "ota"

    # Add section header for testing
    section_start "testing" ":test_tube: Test Suite Execution"
    log_step_start "Running test suites"
    log_step_start "Unit tests"
    log_step_command "./run_unit_tests.sh"
    log_step_log_output "Unit test output:
[ RUN      ] TestCoreFunction1
[       OK ] TestCoreFunction1
[ RUN      ] TestCoreFunction2
[       OK ] TestCoreFunction2
[ RUN      ] TestUtilityModule1
[       OK ] TestUtilityModule1
[ RUN      ] TestUtilityModule2
[  FAILED  ] TestUtilityModule2"
    log_step_pass "Core functions: 50/50 passed"
    log_step_pass "Utility modules: 30/32 passed"
    log_warn "2 tests skipped in Utility modules"
    log_step_done "Unit tests completed"

    log_step_start "Integration tests"
    log_step_command "./run_integration_tests.sh"
    log_step_log_output "Integration test output:
[ RUN      ] TestAPIIntegration
[       OK ] TestAPIIntegration
[ RUN      ] TestDatabaseIntegration
[  FAILED  ] TestDatabaseIntegration"
    log_step_pass "API integration: 20/20 passed"
    log_step_failed "Database integration: 18/20 passed. Test case DB-05 failed: Connection timeout. Test case DB-07 failed: Unexpected query result."
    log_step_done "Integration tests completed"

    log_step_start "System tests"
    log_step_command "./run_system_tests.sh"
    log_step_log_output "System test output:
[ RUN      ] TestBootSequence
[       OK ] TestBootSequence
[ RUN      ] TestPowerManagement
[       OK ] TestPowerManagement
[ RUN      ] TestCommunicationProtocols
[       OK ] TestCommunicationProtocols"
    log_step_pass "Boot sequence: Passed"
    log_step_pass "Power management: Passed"
    log_step_pass "Communication protocols: Passed"
    log_step_done "System tests completed"
    log_done "All tests completed"
    section_end "testing"

    # Add section header for cleanup
    section_start "cleanup" ":broom: Cleanup Operations"
    log_start "Performing cleanup"
    log_step_start "Removing temporary build files"
    log_step_command "rm -rf build/"
    log_step_pass "Build directory cleaned"
    log_step_start "Archiving logs"
    log_step_command "tar -czf logs.tar.gz logs/"
    log_step_pass "Build logs archived"
    log_done "Cleanup completed"
    section_end "cleanup"

    log_done "Firmware build process completed"
    log_info "Firmware" "binary" "firmware-v2.1.bin" "package" "firmware-v2.1.zip"
    log_success "Firmware build completed successfully"
}
