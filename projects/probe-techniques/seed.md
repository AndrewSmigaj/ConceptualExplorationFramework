# Seed technique: the mass-mean probe

*The seed for the technique-invention project, drafted 2026-09-29 for review. The system's job is to invent new techniques for finding and reading a language model's internal representations, starting from this one. It is written in the project's own words.*

## What it does

A mass-mean probe finds the direction in a model's activation space that separates two things the model represents, and places any token along that direction.

1. **Choose two contrasting sets of inputs,** one for each thing: true and false statements, or the same sentence with "he" and with "she", or a model's refusals and its compliances.
2. **Run them through the model** and record the residual-stream activation at one layer, at a chosen token position (often the last token).
3. **Take the mean of each set.** Call them m_A and m_B.
4. **The axis is their difference,** d = m_A − m_B. Its midpoint, (m_A + m_B) / 2, marks the boundary between the two.
5. **Place any token on the axis:** subtract the midpoint from its activation and take the dot product with d, divided by d's length. Positive leans towards A, negative towards B, and the size says how far.

No training is involved. The whole probe is two averages and a subtraction.

## What it is used for

- **Reading:** where a token sits between two representations, and how that changes across tokens, layers or prompts.
- **Classifying:** thresholding the position at the midpoint.
- **Steering:** adding a multiple of d to the activations to push the model towards A.
- **Removing:** projecting d out of the activations to test whether the model needs that direction.

## Why it is a good seed

- **Simple and hard to beat.** With no training, it cannot overfit to accidental features of the training sets, and its directions often generalise to new data better than a trained logistic-regression probe.
- **Causally useful.** The same direction can often steer the model, not just classify its states.

## What it leaves open

These are the known limits, and so the obvious places to improve it. A default model is likely to propose most of them, so they are where the evolved ideas should *not* stop.

- **It captures everything that differs between the two sets,** wanted or not: length, topic, token identity and position all end up in d.
- **It is one dimension.** If the difference is spread over several directions, curved, or depends on context, it is flattened into one line.
- **It is one layer and one token position,** chosen by hand, although representations move and rotate from layer to layer.
- **Positions are distorted by the space's geometry:** a few dimensions with huge variance dominate dot products unless the space is whitened, and whitening improves classification but tends to weaken steering.
- **Finding a direction is not showing the model uses it.** A readable axis can be one the model never reads.
- **It needs labelled contrast sets,** so it only finds distinctions someone already thought to look for.

## The task

Invent techniques that let a researcher learn something about a model's internal representations that the mass-mean probe cannot tell them. A technique should be concrete enough to implement, and testable on an open-weights model with one GPU.
