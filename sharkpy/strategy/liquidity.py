""" Liquidity related strategies
"""
import random
import math
from functools import lru_cache

@lru_cache(maxsize=40)
def _sin(numerator: int, donimator: int) -> float:
    """ Calculate sine function
    """
    return math.sin(numerator * math.pi / donimator)

def gen_amt_dist(base_amt: float, size: int, side: str):
    """ Generate order book
        5 levels:  near end[1] + middle[2-5] + far end[none]
        10 levels: near end[1] + middle[2-8] + far end[9-10]
        20 levels: near end[1-2] + middle[3-15] + far end[16-20]
        35 levels: near end[1-3] + middle[4-26] + far end[27-35]
        50 levels: near end[1-5] + middle[6-37] + far end[38-50]
    """
    asymmetry = 0.98 if side == 'BUY' else 1.02
    near_psychological = 1.1
    psychological = 1.3
    near_noise = random.uniform(0.95, 1.05)
    near_defense_noise = random.uniform(1.2, 1.6)
    far_noise = random.uniform(0.75, 1.25)

    near_base_amt = base_amt * asymmetry
    mid_base_amt = base_amt * asymmetry * random.uniform(0.85, 1.15) # mid_noise
    far_base_amt = base_amt * asymmetry * random.uniform(1.1, 1.4)   # far_defense_noise
    if size <= 5:
        # market_factor * noise_factor (* psychological)
        amounts = [
            # near
            near_base_amt * 0.25 * near_noise,
            # mid
            mid_base_amt * (0.75 + 0.25 * _sin(1, 4)),
            mid_base_amt * (0.75 + 0.25 * _sin(2, 4)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(3, 4)),
            mid_base_amt * (0.75 + 0.25 * _sin(4, 4)) * psychological,
        ]
    elif size <= 10:
        # market_factor * noise_factor (* psychological)
        amounts = [
            # near
            near_base_amt * 0.25 * near_noise,
            # mid
            mid_base_amt * (0.75 + 0.25 * _sin(1, 7)),
            mid_base_amt * (0.75 + 0.25 * _sin(2, 7)),
            mid_base_amt * (0.75 + 0.25 * _sin(3, 7)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(4, 7)),
            mid_base_amt * (0.75 + 0.25 * _sin(5, 7)),
            mid_base_amt * (0.75 + 0.25 * _sin(6, 7)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(7, 7)),
            # far
            far_base_amt * random.uniform(0.8, 1.2),
            base_amt * 0.3 * far_noise,
        ]
    elif size <= 20:
        # market_factor * noise_factor (* psychological)
        amounts = [
            # near
            near_base_amt * 0.25 * near_noise,
            near_base_amt * 0.25 * near_defense_noise * near_psychological,
            # mid
            mid_base_amt * (0.75 + 0.25 * _sin(1, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(2, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(3, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(4, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(5, 13)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(6, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(7, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(8, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(9, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(10, 13)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(11, 13)),
            mid_base_amt * (0.75 + 0.25 * _sin(12, 13)) ,
            mid_base_amt * (0.75 + 0.25 * _sin(13, 13)),
            # far
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            base_amt * 0.38 * far_noise,
        ]
    elif size <= 35:
        # market_factor * noise_factor (* psychological)
        amounts = [
            # near
            near_base_amt * 0.25 * near_noise,  # thin
            near_base_amt * 0.25 * near_defense_noise,  # thick
            near_base_amt * 0.275 * near_defense_noise * near_psychological, # thicker
            # mid
            mid_base_amt * (0.75 + 0.25 * _sin(1, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(2, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(3, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(4, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(5, 23)) * psychological, # psychological price control
            mid_base_amt * (0.75 + 0.25 * _sin(6, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(7, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(8, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(9, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(10, 23)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(11, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(12, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(13, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(14, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(15, 23)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(16, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(17, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(18, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(19, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(20, 23)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(21, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(22, 23)),
            mid_base_amt * (0.75 + 0.25 * _sin(23, 23)),
            # far
            far_base_amt * random.uniform(0.8, 1.2), # far end not displayed
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            base_amt * 0.34 * far_noise,
        ]
    else: #size >= 50:
        # market_factor * noise_factor (* psychological)
        amounts = [
            # near
            near_base_amt * 0.25 * near_noise,
            near_base_amt * 0.25 * near_defense_noise,
            near_base_amt * 0.275 * near_defense_noise * near_psychological,
            near_base_amt * 0.305 * near_defense_noise,
            near_base_amt * 0.275 * near_defense_noise * near_psychological,
            # mid
            mid_base_amt * (0.75 + 0.25 * _sin(1, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(2, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(3, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(4, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(5, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(6, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(7, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(8, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(9, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(10, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(11, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(12, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(13, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(14, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(15, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(16, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(17, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(18, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(19, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(20, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(21, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(22, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(23, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(24, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(25, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(26, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(27, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(28, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(29, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(30, 32)) * psychological,
            mid_base_amt * (0.75 + 0.25 * _sin(31, 32)),
            mid_base_amt * (0.75 + 0.25 * _sin(32, 32)),
            # far
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            far_base_amt * random.uniform(0.8, 1.2),
            base_amt * 0.34 * far_noise,
        ]
    return amounts[:size]
