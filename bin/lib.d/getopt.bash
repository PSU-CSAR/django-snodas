#!/usr/bin/env bash
#
# Released under the MIT license at
# https://gist.github.com/jkeifer/62ab2ce30254923f2ecf791f61871490
#
# Copyright 2021 - 2023 Jarrett Keifer <jkeifer0@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


set -euo pipefail


# check if we have been sourced
# is so we don't print the args at the end
(return 0 2>/dev/null) && SOURCED=true || SOURCED=false


declare -a OPTS
declare -a ARGS
OPTS=()
ARGS=()


usage () {
    cat >&2 <<EOF
USAGE: $0 [OPTIONS] -- [TO_PARSE]

In general, this script is intended to mimic basic usage
of the gnu getopt tool in pure bash. Has support for both
short and long options with optional and required arguments.


OPTIONS

    -h/--help         This usage information.
    -o/--options      Short one-char options to be recognized.
    -l/--longoptions  Long multi-char options to be recognized, separated by commas.
    -n/--name         The script name used in reporting argument errors.
    --                Separator of options to this script from the arguments to parse.

Note that for both short and long options a trailing ':' indicates a
required argument, and a trailing '::' indicates an optional argument.


EXAMPLE

Running:

    $0 -o "r:s::t" --longoptions "redo:,stop::,time" -- \\
        -s -tr hello world "" --redo="some routine" "another routine" --stop yes --time abcd -- --and 'other input'

Yields:

    -s

    -t
    -r
    hello
    --redo
    some routine
    --stop
    yes
    --time
    --
    world

    another routine
    abcd
    --and
    other input

The output can be parsed using a while loop with a case statement
matching on each option name, like getopt. Add a case for
'--' and break parsing, leaving the positional arguments in
order.

Note that newlines in the arguments are not supported. If such support is
required, this script can also be sourced, which will provide access to two
bash arrays: '\$OPTS' and '\$ARGS'.  The '\$OPTS' can similarly be iterated
with a case statement like the output above, but will retain newlines any array
elements.
EOF
}


get_opt_value () {
    # we pass two values into this function;
    # if the first value is not "" then we want to use it,
    [ "$1" == "" ] || {
        # option like "-r=something"
        VAL="${1:1}"
        return
    }

    # else we want to use the second value
    # option like "-r something", but not "-r -t"
    if [ "${2:0:1}" == "-" ]; then
        VAL=""
    else
        VAL="$2"
        ARG_INDEX=$((ARG_INDEX+1))
    fi
}


parse_long_opt () {
    local WORD1="$1"
    local WORD2="$2"
    local OFFSET=2
    local PREFIX="--"
    local FOUND=false

    local OPT=${WORD1%%=*}
    for LOPT in "${LOPTS[@]}"; do
        [ "$OPT" == "${PREFIX}${LOPT%%:*}" ] || continue
        FOUND=true
        # grep to match just the colons at end of matched ref long opt, if any
        case "$(<<<"${LOPT}" grep -Eo ':+$')" in
            ::)
                # optional arg
                get_opt_value "${WORD1#"$OPT"}" "$WORD2"
                OPTS+=("${OPT}")
                OPTS+=("${VAL}")
                ;;
            :)
                # required arg
                get_opt_value "${WORD1#*"$OPT"}" "$WORD2"
                [ -n "${VAL:-}" ] || { echo >&2 "${NAME+$NAME: }${OPT}: value required"; exit 1; }
                OPTS+=("${OPT}")
                OPTS+=("${VAL}")
                ;;
            "")
                # no arg
                OPTS+=("${OPT}")
                ;;
        esac
        break
    done
    $FOUND || {
        echo >&2 "${NAME+$NAME: }${OPT}: unknown option"
        exit 1
    }
}


parse_short_opt () {
    local WORD1="$1"
    local WORD2="$2"
    local OFFSET=1
    local PREFIX="-"
    local FOUND=false

    for ((i=OFFSET; i<${#WORD1}; ++i)); do
        OPT=${WORD1:i:1}
        FOUND=false

        # when we have an "=" like "-r=some-value"
        # we break out because look-ahead has already
        # processed this char
        [ "$OPT" != "=" ] || break

        for ((j=0; j<${#SOPTS}; ++j)); do
            [ "$OPT" == "${SOPTS:j:1}" ] || continue
            FOUND=true
            case "${SOPTS:j+1:2}" in
                =|[[:space:]])
                    FOUND=true
                    break
                    ;;
                ::)
                    # optional arg
                    get_opt_value "${WORD1:$i+1}" "$WORD2"
                    OPTS+=("${PREFIX}${OPT}")
                    OPTS+=("${VAL}")
                    ;;
                :*)
                    # required arg
                    get_opt_value "${WORD1:$i+1}" "$WORD2"
                    [ -n "${VAL:-}" ] || { echo >&2 "${NAME+$NAME: }${PREFIX}${OPT}: value required"; exit 1; }
                    OPTS+=("${PREFIX}${OPT}")
                    OPTS+=("${VAL}")
                    ;;
                *)
                    # no arg
                    OPTS+=("${PREFIX}${OPT}")
                    ;;
            esac
            break
        done
        $FOUND || {
            echo >&2 "${NAME+$NAME: }${PREFIX}${OPT}: unknown option"
            exit 1
        }
    done
}


parse_opt () {
    local WORD1="$1"
    local WORD2="$2"

    case "$WORD1" in
        --*)
            parse_long_opt "$@"
            ;;
        -*)
            parse_short_opt "$@"
            ;;
        *)
            echo >&2 "Unknown option prefix"
            exit 1
            ;;
    esac

}


parse_opts_args () {
    local NEXT N ARG_INDEX
    for ((ARG_INDEX=1; ARG_INDEX<=$#; ++ARG_INDEX)); do
        ARG="${!ARG_INDEX}"

        case $ARG in
            --)
                ARGS=( "${ARGS:+"${ARGS[@]}" }" "${@:$ARG_INDEX+1}" )
                break
                ;;
            -*)
                N=$((ARG_INDEX+1))
                NEXT=""
                [ $N -le $# ] && NEXT="${!N}"
                parse_opt "$ARG" "${NEXT}"
                ;;
            *)
                ARGS+=("$ARG")
                ;;
        esac
    done
}


main () {
    local ARG SOPTS _LOPTS LOPTS
    while [ $# -gt 0 ]; do
        ARG=$1
        shift ||:
        case "$ARG" in
            -o|--options)
                SOPTS="$1"
                shift ||:
                ;;
            -l|--longoptions)
                _LOPTS="$1"
                shift ||:
                ;;
            -n|--name)
                NAME="$1"
                shift ||:
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                break
                ;;
            *)
                echo >&2 "unknown option: '$ARG'"
                usage
                exit 1
                ;;
        esac
    done

    [ -n "${SOPTS:-}" ] || [ -n "${_LOPTS:-}" ] || {
        echo >&2 "error: no short or long options declared"
        usage
        exit 1
    }

    IFS=',' read -ra LOPTS <<< "${_LOPTS:-}"

    parse_opts_args "$@"
    ${SOURCED} || printf '%s\n' ${OPTS:+"${OPTS[@]}"} -- ${ARGS:+"${ARGS[@]}"}
}


main "$@"
