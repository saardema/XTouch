from ctrl_mix.core.engine import Engine
from motu.mixer import MotuGroup, MotuInput


def setup_main_mix():
    for i, strip in engine.assignments.main_mix.items():
        encoder, fader, button = engine.controller.get_channel_strip(i)

        # Fader => Channel strip fader
        engine.assign(fader, strip.channel.fader)

        # Top encoder => Group sends
        if isinstance(strip.channel, (MotuInput, MotuGroup)):
            engine.assign(encoder, strip.channel.main_send)

        # Top button => Mute toggle
        engine.assign(button, strip.channel.mute)
        button.is_toggle = True

    # Main mix fader
    engine.assign(engine.controller.main_faders[0], engine.mixer.main.fader)
    engine.mixer.main.fader.max_val = 1.0


def on_channel_selected(layer: int, ch: int):
    assign_side_encoder_as_aux(layer, ch)
    assign_channel_encoders_as_group_sends(layer, ch)


def on_channel_unselected(layer: int, prev_ch: int):
    unassign_side_encoders(layer)
    restore_channel_encoders(layer)


def restore_channel_encoders(layer):
    pairs = list(zip(
        engine.assignments.main_mix.values(),
        engine.controller.channel_encoders))

    pairs = pairs[:8] if layer == 0 else pairs[8:]

    for i, strip in engine.assignments.main_mix.items():
        encoder = engine.controller.channel_encoders[i]
        if isinstance(strip.channel, (MotuInput, MotuGroup)):
            engine.assign(encoder, strip.channel.main_send)


def unassign_side_encoders(layer: int):
    for enc in engine.controller.side_encoders[layer]:
        engine.assignments.unassign(enc)
        engine.controller.set_control(enc, 0)


def assign_side_encoder_as_aux(layer: int, ch: int):
    chan = engine.assignments.main_mix[ch].channel

    if isinstance(chan, (MotuInput, MotuGroup)):
        for enc, aux in zip(engine.controller.side_encoders[layer], avail_aux_ch):
            param = chan.aux_sends[aux.channel_number]
            engine.assign(enc, param)


def assign_channel_encoders_as_group_sends(layer: int, ch: int):
    chan = engine.assignments.main_mix[ch].channel

    if isinstance(chan, MotuInput):
        encs = engine.controller.channel_encoders
        encs = encs[:8] if layer == 0 else encs[8:]
        sends = iter(avail_groups)
        for enc in encs:
            if enc == encs[-1]:
                param = chan.main_send
            else:
                send = next(sends, None)
                param = chan.group_sends[send.channel_number] if send else None
            engine.assign(enc, param)


if __name__ == "__main__":
    engine = Engine()
    avail_aux_ch = [aux.channel for aux in engine.assignments.aux.values() if aux.cfg.send_enabled]
    avail_groups = [group.channel for group in engine.assignments.groups.values() if group.cfg.send_enabled]

    engine.mixer.sync_to_store()
    setup_main_mix()

    engine.on(engine.ChannelUnselected, on_channel_unselected)
    engine.on(engine.ChannelSelected, on_channel_selected)
