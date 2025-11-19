from agents import Agent, function_tool
from pydantic import BaseModel



PROMPT = """
You are an expert personality judge for job interview preparation plans. Your task is to assess how compatible the plan is
with the candidate's personality traits and suggest adjustments.
"""

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_ENTJ_personality_traits() -> str:
    """Returns a description of the ENTJ personality traits."""

    overview = """
ENTJs, also known as Commanders, are charismatic, energetic goal-getters who approach every situation with confidence. For this reason, they are often perceived as natural leaders. Moreover, their resilience and ability to think on their feet make them exceptional in leading roles.

Focused on efficiency, ENTJs are big-picture thinkers who are both creative and practical. They know what they want from life and don’t hesitate to go after their dreams. Although they come across as insensitive, their fearless attitude, boundless energy, and unwavering determination never fail to motivate those around them.

"""

    strenghts = """
Strategic leadership
As a result of their exceptional organizational skills, strategic mind, and ability to take into consideration both the big picture and the practical aspects of any issue, ENTJs thrive in positions of leadership.

Determination
One reason ENTJs are often exceptionally successful is that they will stop at nothing to achieve their goals. Always knowing exactly what they want out of life, they make the most of their skills and resources to achieve their goals.

Problem-solving ability
Coming up with fresh, original ideas is second nature to ENTJs because of their capacity to think both logically and creatively. For this reason, they can see any problem from multiple perspectives and offer innovative, effective solutions quickly.

Courage
Enthusiastic, passionate, and energetic, ENTJs show great courage in the face of all kinds of challenges. This is why people are often drawn to them despite their lack of warmth, as they feel they can rely on ENTJs in the toughest times.
"""

    weaknesses = """
Insensitivity
ENTJs have a hard time expressing their emotions and often believe that suppressing feelings is necessary to achieve success. They also show little interest in how other people feel, not because they don’t care about people but because they believe that feelings don’t matter. As a result, they easily earn the reputation of being arrogant or aloof.

Rigidity
ENTJs can sometimes let their success go to their heads too much and, as a result, insist on their own ideas and methods, refusing to consider other people’s perspectives. While this kind of self-assurance is a hallmark of charismatic leaders, it can also cause them to miss out on amazing opportunities and important people.

Bluntness
Prioritizing logic over empathy and focusing on efficiency, ENTJs often fail to understand that honesty isn’t the best policy in every situation. Their lack of tact and empathy and insistence on facts often cause friction in their relationships with other people.

Impatience
Due to their high standards and desire for swift progress, ENTJs easily get frustrated with tasks that require a slower pace and attention to detail. Their impatience may lead to outbursts of anger and frustration in situations that are not actually that stressful.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTJ_personality_traits() -> str:
    """Returns a description of the INTJ personality traits."""

    overview = """
The INTJ personality type is rational, analytical, and highly individualistic, always challenging the status quo and looking for ways to improve the existing systems.

With an innate ability to spot patterns and make connections between objects, INTJs are excellent problem-solvers and welcome employees in any field. However, they are also highly ambitious, always striving to improve themselves and rarely settling for less than they think they deserve.

In their quest for excellence, INTJs rely on their impeccable intuition and sharp wit. They don’t typically succumb to peer pressure or outward influences—they may take their loved ones’ opinions into account when making decisions but ultimately follow their own path.

Their independence and their general aversion to emotional outbursts may make them appear cold, detached, or downright intimidating. However, those who break through their hard shell will discover that INTJs have a softer side, too, and that they deeply value their loved ones, even if they don’t always show it.
"""

    strenghts = """
Independence
INTJs prefer to march to the beat of their own drum, disregarding what others might think of their often unconventional ways. They hate being told what to do, especially when they can see no logic in it. As a result, INTJs are frequently perceived as contrarians or “lone wolf” types.

Confidence
INTJs know how capable they are, and they are proud of it, too. This quiet confidence shines through in their words and actions, making them seem self-assured and reliable. Due to their calm, aloof demeanor, it can also come across as arrogance—though INTJs rarely brag or boast about their achievements.

Open-minded
INTJs question everything and hate accepting existing beliefs just because others tell them so. Instead, they seek their own truth and believe in radical change if it means making current systems more efficient.

Rational
INTJs are masters of logic, fully relying on it when solving problems in their professional and private lives. Nothing is too challenging for these sharp minds, and, in fact, they tend to enjoy solving the seemingly unsolvable.
"""

    weaknesses = """

Excessive perfectionism
INTJs are perfectionists to the core, and while this benefits them in some ways, it also limits their potential in others. They hold themselves to a high standard and easily become disappointed when they can’t meet it.

Lower emotional intelligence
INTJs struggle with expressing and understanding emotions and may accidentally come across as cold and callous. Sometimes, they do it on purpose—some INTJs are dismissive of emotions and impatient around people who value them above rationality and logic.

Extremely private
Like most introverts, INTJs prefer to keep their personal matters away from prying eyes. However, they can take it too far, closing themselves off even to their loved ones.

Blunt
INTJs like to tell it how it is but often forget that even the hard truth can be delivered with tact and kindness. As a result, their words may seem overly harsh and inadvertently hurt the other person.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_ENTP_personality_traits() -> str:
    """Returns a description of the ENTP personality traits."""

    overview = """
The ENTP personality type is characterized by an innate desire to challenge the status quo. While they can be rebellious, ultimately, ENTPs seek to become catalysts for change rather than simply cause chaos.

Logical yet creative, they approach problems with vigor, curiosity, and creativity, displaying a remarkable ability to analyze situations from different angles. Rather than getting caught up in details, they strive to see the whole picture, allowing them to not only identify the cause of problems but also find unprecedented solutions to them.

ENTPs aren’t called “Debaters” without good reason; their love for lively—and even heated—discussions is often the first thing others notice about them. They aren’t afraid to express their honest opinions, question other people’s beliefs, deconstruct their arguments, and point out logical flaws in them. On the contrary, they get a kick out of it!

"""

    strenghts = """

Curiosity
The insatiable craving for intellectual stimulation prompts ENTPs to constantly seek new knowledge and keep an open mind. While they may not always agree with other people’s opinions, they are eager to hear them (and challenge them, of course!).

Boldness
The ENTP personality has no shortage of self-confidence. Not only does this help ENTPs receive criticism without taking it personally, but it also inspires them to take risks. Most importantly, they don’t let failure stop them from achieving their goals.

Flexibility
Sharp-witted and spontaneous, ENTPs have a natural talent for improvisation and enjoy taking on new challenges. They have no trouble adapting to changes and can make any challenging situation work in their favor.

Originality
ENTPs can’t help but question tradition and look for new and improved ways of doing things. This, coupled with their passion for exploring possibilities, grants them the ability to come up with original ideas and unorthodox solutions to problems.
"""

    weaknesses = """
Impracticality
While ENTPs are fascinated with ideas, they are much less interested in taking action and turning them into reality. Since they struggle with organization, structure, and the like, they may also neglect everyday tasks, such as household chores.

Inconsideration
Since ENTPs lead with logic and rationality, they often forget to pay enough attention to other people’s emotions. Sometimes, they can get so wrapped up in a debate that they don’t even notice when they start pushing other people’s boundaries.

Hyper-independence
Though generally flexible, ENTPs can be independent to the point of stubbornness. Their non-conformist attitude and desire for autonomy can cause them to resist authority and break rules, even when it isn’t in their best interest to do so.

Trouble concentrating
ENTPs’ active minds can make it challenging for them to focus, and it doesn’t help that they are also prone to boredom. Once the novelty of an idea wears off, they jump to the next one, often leaving behind a trail of unfinished projects.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"

def get_INTP_personality_traits() -> str:
    """Returns a description of the INTP personality traits."""

    overview = """
The INTP personality type is driven by a desire to understand the underlying principles of life, the universe, and everything around them. Endowed with deeply analytical and curious minds, INTPs are natural-born philosophers, innovators, and problem solvers who never cease to ask questions.

Their deep-seated belief that everything can—and should—be questioned prompts them to seek truth, challenge traditions, and invent new ways of looking at things. It also underpins their approach toward life; in their eyes, life is meant to be understood, not just lived. And indeed, many of them spend more time pondering about life than actually experiencing it!

As quiet and detached as they may seem, INTPs relish thought-provoking conversations, be they scientific or philosophical. Nonetheless, they are far more interested in ideas than people.

"""

    strenghts = """
Analytical thinking
INTPs are the embodiment of free-thinking; they question everything and take nothing at face value. Burning with a desire to uncover the truth, they look beneath the surface, dissecting and critically evaluating information to understand the forces at play before making any judgments.

Inventiveness
INTPs favor innovation over tradition. Combined with their rich imagination, future-oriented mindsets, and aptitude for looking at things from different angles, this helps them produce original ideas and unconventional solutions to problems

Inquisitive mind
Intellectual curiosity is the hallmark of the INTP personality. Their insatiable hunger for knowledge and intellectual stimulation causes them to constantly seek out new things to learn. They enjoy learning for the sake of learning, even if the knowledge has no practical purpose.

Impartiality
In their search for truth, INTPs keep their feelings at bay and strive to be objective at all times. They also remain open to the possibility of changing their views over time if new evidence presents itself.
"""

    weaknesses = """
Impracticality
Deeply devoted to intellectual pursuits, INTPs tend to neglect the mundane aspects of life. Staying grounded in the present is challenging for them; their thoughts can consume them to the point where they forget to pay bills, do chores, etc.

Lack of sensitivity
Being highly logical and objective, INTPs tend to underestimate the value of emotions. Since they see them as fleeting and insignificant, they often struggle to understand other people’s feelings and can come across as cold and inconsiderate.

Impatience
Though reserved, INTPs enjoy sharing their ideas and knowledge with others. However, they can get quickly frustrated with people who struggle to keep up with them intellectually or simply aren’t interested in theoretical discussions.

Overthinking
Although their active minds help INTPs come up with brilliant ideas, they also make them susceptible to overthinking and anxiety. Their tendency to worry that there’s something they’re missing in the big picture makes them prone to self-doubt.
    """

    return f"Personality Overview:\n{overview}\nStrengths:\n{strenghts}\nWeaknesses:\n{weaknesses}"


class Advice(BaseModel):
    summary: str
    """A brief summary of the analysis and suggested improvements."""

personality_judge_agent = Agent(
    name="Personality Judge Agent",
    model="gpt-5-nano",
    instructions=PROMPT,
    output_type=Advice
)