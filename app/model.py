
from dataclasses import dataclass;
from typing import Optional, Array


@dataclass
class Profile:
    name: str


@dataclass
class Deck:
    profile: Profile
    parent_deck: Optional(Deck)
    title: str
    sound_clips: Array[SoundClip]


@dataclass
class MyDate:
   year: int
   month: int
   day: int

class SoundFile: 
    sound_file_id: int


class SoundClip: 
    deck: Deck
    created_date: MyDate
    first_review_date: MyDate
    lastest_review_date: MyDate
    due: MyDate
    interval_days: int
    num_reviews: int
    






