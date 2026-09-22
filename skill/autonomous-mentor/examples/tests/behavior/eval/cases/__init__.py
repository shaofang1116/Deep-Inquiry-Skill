"""三类命题 eval 用例。"""

from tests.behavior.eval.cases.concept import ConceptCase
from tests.behavior.eval.cases.controversy import ControversyCase
from tests.behavior.eval.cases.mechanism import MechanismCase

ALL_CASES = [MechanismCase, ConceptCase, ControversyCase]
