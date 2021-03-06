import copy
import json

from Game.GameObject import GameObject
from Game.GameMode import GameMode

from python_digits import DigitWord
from flask_helpers.VersionHelpers import VersionHelpers
from python_cowbull_server import error_handler


class GameController(object):
    """
    GameController - Provides the controller functions (execute_load, save, and guess) to
    interact with a CowBull game.

    Originally, the GameController was a separate Python
    package deployed to PyPi; however, there wasn't really much need for the game to
    exist outside the game server, so a decision was made to relocate the package into
    the game server (this can easily be undone at any time).

    """
    GAME_PLAYING = "playing"    # The game is in progress.
    GAME_WAITING = "waiting"    # The game is waiting to start - not currently used.
    GAME_WON = "won"            # The game is over and has been won.
    GAME_LOST = "lost"          # The game is over and has been lost.

    version_helper = VersionHelpers()
    STRINGY = version_helper.STRINGTYPE

    def __init__(self, game_json=None, game_modes=None, mode=None):
        """
        Initialize a GameController object to allow the game to be played. The controller
        creates a game object (see GameObject.py) and allows guesses to be made against
        the 'hidden' object.

        :param game_json: <optional>, if provided is a JSON serialized representation
        of a game; if not provided a new game is instantiated.
        :param game_modes: <optional>, a list of GameMode objects representing game modes.
        :param mode: <optional>, the mode the game should be played in; may be a GameMode
        object or a str representing the name of a GameMode object already defined (e.g.
        passed via game_modes).
        """
        # execute_load error handler
        self.handler = error_handler
        self.handler.module = "GameController"
        self.handler.method = "__init__"

        # Set defaults
        self.default_mode = None

        # Dump parameters to log
        self.handler.log(message="Parameter game_modes: Value {} Type {}".format(game_modes, type(game_modes)))
        self.handler.log(message="Parameter mode: Value {} Type {}".format(mode, type(mode)))
        self.handler.log(message="Parameter game_json: Value {} Type {}".format(game_json, type(game_json)))

        # execute_load game_modes
        self.handler.log(message="Setup game modes")
        self._game_modes = None
        self.load_modes(input_modes=game_modes)

        # execute_load any game passed
        self.handler.log(message="Loading any saved game")
        self.game = None
        self.load(game_json=game_json, mode=mode)

    #
    # Properties
    #

    @property
    def game_modes(self):
        return sorted(self._game_modes, key=lambda x: x.priority)

    @property
    def game_mode_names(self):
        return [game_mode.mode for game_mode in sorted(self._game_modes, key=lambda x: x.priority)]

    #
    # 'public' methods
    #

    def guess(self, *args):
        """
        Make a guess, comparing the hidden object to a set of provided digits. The digits should
        be passed as a set of arguments, e.g:

        * for a normal game: 0, 1, 2, 3
        * for a hex game: 0xA, 0xB, 5, 4
        * alternate for hex game: 'A', 'b', 5, 4

        :param args: An iterable of digits (int or str)
        :return: A dictionary object detailing the analysis and results of the guess
        """

        self.handler.method="guess"
        self.handler.log(message="Validating game is defined")
        if self.game is None:
            raise ValueError("The Game is unexpectedly undefined!")

        self.handler.log(message="Building empty response object")
        response_object = {
            "bulls": None,
            "cows": None,
            "analysis": None,
            "status": None
        }

        self.handler.log(message="Checking game status")
        if self.game.status == self.GAME_WON:
            self.handler.log(message="Game already won")
            response_object["status"] = \
                self._start_again_message("You already won!")
        elif self.game.status == self.GAME_LOST:
            self.handler.log(message="Game already lost")
            response_object["status"] = \
                self._start_again_message("You already lost!")
        elif self.game.guesses_remaining < 1:
            self.handler.log(message="Game lost, too many guesses")
            response_object["status"] = \
                self._start_again_message("You've made too many guesses")
        else:
            self.handler.log(message="Game is valid and in play")

            guess_made = DigitWord(*args, wordtype=self.game.mode.digit_type)
            self.handler.log(
                message="Created DigitWord using digits provided: Value {} Type {}"
                    .format(guess_made.word, type(guess_made))
            )

            self.handler.log(message="Comparing guess and answer")
            comparison = self.game.answer.compare(guess_made)

            self.handler.log(message="Increment number of guesses made")
            self.game.guesses_made += 1
            response_object["bulls"] = 0
            response_object["cows"] = 0
            response_object["analysis"] = []

            self.handler.log(message="Process comparison analysis")
            for comparison_object in comparison:
                self.handler.log(message="Processing index {} value {}".format(
                    comparison_object.index,
                    comparison_object.digit
                ))
                if comparison_object.match:
                    response_object["bulls"] += 1
                elif comparison_object.in_word:
                    response_object["cows"] += 1
                response_object["analysis"].append(comparison_object.get_object())

            if response_object["bulls"] == self.game.mode.digits:
                self.game.status = self.GAME_WON
                self.game.guesses_made = self.game.mode.guesses_allowed
                response_object["status"] = self._start_again_message(
                    "Congratulations, you win!"
                )
                self.handler.log(
                    message="The game has been won with the answers: {}"
                        .format(guess_made.word)
                )
            elif self.game.guesses_remaining < 1:
                self.game.status = self.GAME_LOST
                response_object["status"] = self._start_again_message(
                    "Sorry, you lost!"
                )
                self.handler.log(method="guess", message="Game lost.")
            else:
                self.game_status = self.GAME_PLAYING
                response_object["status"] = "You have {} bulls and {} cows".format(
                    response_object["bulls"],
                    response_object["cows"]
                )
                self.handler.log(
                    message="Still in play. {} bulls, {} cows"
                        .format(response_object["bulls"], response_object["cows"])
                )

        return response_object

    def load(self, game_json=None, mode=None):
        """
        Load a game from a serialized JSON representation. The game expects a well defined
        structure as follows (Note JSON string format):

        '{
            "guesses_made": int,
            "key": "str:a 4 word",
            "status": "str: one of playing, won, lost",
            "mode": {
                "digits": int,
                "digit_type": DigitWord.DIGIT | DigitWord.HEXDIGIT,
                "mode": GameMode(),
                "priority": int,
                "help_text": str,
                "instruction_text": str,
                "guesses_allowed": int
            },
            "ttl": int,
            "answer": [int|str0, int|str1, ..., int|strN]
        }'

        * "mode" will be cast to a GameMode object
        * "answer" will be cast to a DigitWord object

        :param game_json: The source JSON - MUST be a string
        :param mode: A mode (str or GameMode) for the game being loaded
        :return: A game object
        """

        self.handler.method = "execute_load"
        self.handler.log(message="Validating mode value")
        self.handler.log(message="Mode: Value {} Type {}".format(mode, type(mode)))
        _mode = mode or 'Normal' # Default mode to normal if not provided

        self.handler.log(message="Validating (any) JSON provided")
        if game_json is None:    # New game_json
            self.handler.log(message="No JSON, so start new game.")
            self.handler.log(message="Validating (any) mode provided")
            if mode is not None:
                self.handler.log(message="mode provided, checking if string or GameMode")
                if isinstance(mode, self.STRINGY):
                    self.handler.log(message="Mode is a string; matching name {}".format(mode))
                    _game_object = GameObject(mode=self._match_mode(mode=mode))
                elif isinstance(mode, GameMode):
                    self.handler.log(message="Mode is a GameMode object")
                    _game_object = GameObject(mode=mode)
                else:
                    self.handler.log(message="Mode is invalid")
                    raise TypeError("Game mode must be a GameMode or string")
            else:
                self.handler.log(message="Game mode is None, so default mode used.")
                _game_object = GameObject(mode=self._game_modes[0])
            _game_object.status = self.GAME_PLAYING
        else:
            self.handler.log(message="JSON provided")
            if not isinstance(game_json, self.STRINGY):
                raise TypeError("Game must be passed as a serialized JSON string.")

            self.handler.log(message="Attempting to execute_load")
            game_dict = json.loads(game_json)

            self.handler.log(message="Validating mode exists in JSON")
            if not 'mode' in game_dict:
                raise ValueError("Mode is not provided in JSON; game_json cannot be loaded!")

            _mode = GameMode(**game_dict["mode"])

            if len(game_dict["answer"]) != game_dict["mode"]["digits"]:
                raise ValueError("JSON provided answer does not match the JSON game mode")

            _game_object = GameObject(mode=_mode, source_game=game_dict)

        self.handler.log(message="Deep copy loaded (or new) object")
        self.game = copy.deepcopy(_game_object)

    def save(self):
        """
        Save returns a string of the JSON serialized game object.

        :return: str of JSON serialized data
        """

        return json.dumps(self.game.dump())

    def load_modes(self, input_modes=None):
        """
        Loads modes (GameMode objects) to be supported by the game object. Four default
        modes are provided (normal, easy, hard, and hex) but others could be provided
        either by calling load_modes directly or passing a list of GameMode objects to
        the instantiation call.

        :param input_modes: A list of GameMode objects; nb: even if only one new GameMode
        object is provided, it MUST be passed as a list - for example, passing GameMode gm1
        would require passing [gm1] NOT gm1.

        :return: A list of GameMode objects (both defaults and any added).
        """

        # Set default game modes
        self.handler.method = "load_modes"
        self.handler.log(message="Loading default modes")
        _modes = [
            GameMode(
                mode="Normal",
                priority=20,
                digits=4,
                digit_type=DigitWord.DIGIT,
                guesses_allowed=10,
                help_text="This is the normal (default) game. You need to guess 4 digits "
                          "in the right place and each digit must be a whole number "
                          "between 0 and 9. There are 10 tries to guess the "
                          "correct answer.",
                instruction_text="Enter 4 digits, each digit between 0 and 9 "
                                 "(0, 1, 2, 3, 4, 5, 6, 7, 8, and 9)."
            ),
            GameMode(
                mode="Easy",
                priority=10,
                digits=3,
                digit_type=DigitWord.DIGIT,
                guesses_allowed=6,
                help_text="Easy. You need to guess 3 digits in the right place and each "
                          "digit must be a whole number between 0 and 9. There are "
                          "6 tries to guess the correct answer.",
                instruction_text="Enter 3 digits, each digit between 0 and 9 "
                                 "(0, 1, 2, 3, 4, 5, 6, 7, 8, and 9)."
            ),
            GameMode(
                mode="Hard",
                priority=30,
                digits=6,
                digit_type=DigitWord.DIGIT,
                guesses_allowed=6,
                help_text="Hard. You need to guess 6 digits in the right place and each "
                          "digit must be a whole number between 0 and 9. There are "
                          "only 6 tries to guess the correct answer.",
                instruction_text="Enter 6 digits, each digit between 0 and 9 "
                                 "(0, 1, 2, 3, 4, 5, 6, 7, 8, and 9)."
            ),
            GameMode(
                mode="Hex",
                priority=40,
                digits=4,
                digit_type=DigitWord.HEXDIGIT,
                guesses_allowed=10,
                help_text="Hex. You need to guess 4 digits in the right place and each "
                          "digit must be a hexidecimal number between 0 and F. There are "
                          "10 tries to guess the correct answer.",
                instruction_text="Enter 4 digits, each digit between 0 and F "
                                 "(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, "
                                 "E, and F)."
            )
        ]
        self.handler.log(message="Loaded modes: {}".format(_modes))

        if input_modes is not None:
            if not isinstance(input_modes, list):
                raise TypeError("Expected list of input_modes")

            for mode in input_modes:
                if not isinstance(mode, GameMode):
                    _mode = GameMode(**mode)
                else:
                    _mode = mode
#                    raise TypeError("Expected list to contain only GameMode objects")
                self.handler.log(
                    message="Appending mode: {}".format(mode)
                )
                _modes.append(_mode)

        self.handler.log(message="Deep copying modes")
        self._game_modes = copy.deepcopy(_modes)
        self.default_mode = "Normal"

    #
    # 'private' methods
    #
    def _match_mode(self, mode):
        self.handler.method = "_match_mode"
        self.handler.log(message="Attempting to match mode: {}".format(mode))
        _mode = [game_mode for game_mode in self._game_modes if game_mode.mode == mode]

        if len(_mode) < 1:
            self.handler.log(method="_match_mode", message="No match found for: {}".format(mode))
            raise ValueError("Mode {} not found - has it been initiated?".format(mode))

        _mode = _mode[0]
        if not _mode:
            self.handler.log(
                message="Something unexpected happened while matching mode: {}".format(mode)
            )
            raise ValueError("For some reason, the mode is defined but unavailable!")

        self.handler.log(
            message="Returning mode: {}, value: {}".format(mode, _mode.dump())
        )
        return _mode

    def _start_again_message(self, message=None):
        """Simple method to form a start again message and give the answer in readable form."""
        self.handler.log(method="_start_again_message", message="{}".format(message))
        the_answer = ', '.join(
            [self._non_hex(d) for d in self.game.answer][:-1]
        ) + ', and ' + [self._non_hex(d) for d in self.game.answer][-1]

        return "{0}{1} The correct answer was {2}. Please start a new game.".format(
            message,
            "." if message[-1] not in [".", ",", ";", ":", "!"] else "",
            the_answer
        )

    @staticmethod
    def _non_hex(value):
        return str(value).replace('0x', '').upper()
