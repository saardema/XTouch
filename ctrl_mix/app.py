from ctrl_mix.engine import ChannelConfigMode, Engine
from ctrl_mix.motu.channel import Equalizer, MotuAuxSendCapable, MotuGroupSendCapable, MotuMainSendCapable, MotuMixerChannel
from ctrl_mix.xtouch.control import Encoder


class ConfigModeHandler:
    @staticmethod
    def prepare():
        layer = engine.state.layer
        encs = ctr.side_encoders[layer]
        ch_idx = engine.state.selected_channel[layer]
        chan = mix.main

        if ch_idx != -1:
            candidate = asm.main_mix[ch_idx].channel
            if isinstance(candidate, MotuMixerChannel):
                chan = candidate

        return layer, chan, encs

    @staticmethod
    def enter(): ...

    @staticmethod
    def on_short_press(encoder: Encoder): ...

    @staticmethod
    def on_long_press(encoder: Encoder): ...

    @staticmethod
    def exit(): ...


class DefaultModeHandler(ConfigModeHandler):
    @staticmethod
    def enter():
        layer = engine.state.layer
        encs = ctr.side_encoders[layer]

        for enc in encs:
            enc.is_enabled = False


class AuxModeHandler(ConfigModeHandler):
    @staticmethod
    def enter():
        layer, chan, _ = AuxModeHandler.prepare()

        # Aux sends => Side encoders
        if isinstance(chan, MotuAuxSendCapable):
            engine.assign_encoders(False, engine.get_aux_sends(chan), layer)

        # Main aux => Side encoders
        elif chan is mix.main:
            engine.assign_encoders(False, engine.get_main_out_channels(), layer)


class EqModeHandler(ConfigModeHandler):
    @staticmethod
    def enter():
        _, chan, encoders = EqModeHandler.prepare()

        for enc in encoders:
            enc.tristate_toggle = False

        for i, band in enumerate(chan.eq.get_bands()):
            enc_a = encoders[i * 2]
            enc_b = encoders[i * 2 + 1]
            EqModeHandler.update_band(enc_a, enc_b, band)

    @staticmethod
    def update_band(enc_a: Encoder, enc_b: Encoder, band: Equalizer.Band):
        on = band.enable.normalized

        engine.assign(enc_a, band.gain, on)
        engine.assign(enc_b, band.freq, on)

        enc_a.is_enabled = on
        enc_b.is_enabled = on

    @staticmethod
    def on_short_press(encoder: Encoder):
        layer, chan, encs = EqModeHandler.prepare()

        band = chan.eq.get_bands()[encoder.index % 8 // 2]

        if encoder.index % 2 == 1:

            # Toggle freq / bandwidth encoder
            param = asm.control_to_parameter.get(encoder)
            next_param = band.freq if param == band.bw else band.bw
            engine.assign(encoder, next_param)

        elif band in [chan.eq.lowshelf, chan.eq.highshelf]:

            # Toggle shelf/parametric mode for low and highshelf
            mix.set_parameter(band.mode, 1 - band.mode.value)

    @staticmethod
    def on_long_press(encoder: Encoder):
        if encoder.index % 2 == 1:
            return

        layer, chan, encs = EqModeHandler.prepare()
        band = chan.eq.get_bands()[encoder.index % 8 // 2]
        mix.set_parameter(band.enable, 1 - band.enable.value)
        enc_b = encs[encs.index(encoder) + 1]
        EqModeHandler.update_band(encoder, enc_b, band)

    @staticmethod
    def exit():
        _, _, encoders = EqModeHandler.prepare()
        for enc in encoders:
            enc.tristate_toggle = True


mode_map: dict[ChannelConfigMode, type[ConfigModeHandler]] = {
    ChannelConfigMode.Off: DefaultModeHandler,
    ChannelConfigMode.AuxSends: AuxModeHandler,
    ChannelConfigMode.EQ: EqModeHandler,
    ChannelConfigMode.Compressor: DefaultModeHandler,
    ChannelConfigMode.Gate: DefaultModeHandler,
}


def setup_main_mix():
    for i, strip in asm.main_mix.items():
        encoder, fader, button = ctr.get_channel_strip(i)
        if i == 2:
            pass

        # Channel Main send => Top encoder
        if isinstance(strip.channel, MotuMainSendCapable):
            engine.assign(encoder, strip.channel.main_send)

        # Channel fader => Fader
        engine.assign(fader, strip.channel.fader)

        # Mute toggle => Top button
        engine.assign(button, strip.channel.mute)
        button.is_toggle = True

    # Main mix fader
    engine.assign(ctr.main_faders[0], mix.main.fader)
    mix.main.fader.cfg.max = 1.0


def on_chan_cfg_mode_changed(prev_mode=None):
    if prev_mode:
        mode_map[prev_mode].exit()

    mode_map[engine.state.chan_cfg_mode].enter()


def on_encoder_short_pressed(encoder: Encoder, sub_type):
    mode_map[engine.state.chan_cfg_mode].on_short_press(encoder)


def on_encoder_long_pressed(encoder: Encoder, sub_type):
    mode_map[engine.state.chan_cfg_mode].on_long_press(encoder)


def on_channel_selected(layer: int, ch: int):
    mode_map[engine.state.chan_cfg_mode].enter()
    chan = asm.main_mix[ch].channel

    # Group sends => Channel encoders
    if isinstance(chan, MotuGroupSendCapable):
        engine.assign_encoders(True, engine.get_group_sends(chan), layer)
    else:
        engine.assign_encoders(True, [], layer)

    # Main send => Last channel encoder
    if isinstance(chan, MotuMainSendCapable):
        engine.assign(ctr.channel_encoders[layer * 8 + 7], chan.main_send)


def on_channel_unselected(layer: int, prev_ch: int):
    mode_map[engine.state.chan_cfg_mode].enter()
    setup_main_mix()


def on_channel_reselected(layer: int, prev_ch: int):
    ...


def on_layer_change(layer: int):
    mode_map[engine.state.chan_cfg_mode].enter()

    buttons = ctr.select_buttons + ctr.mute_buttons + ctr.transport_buttons
    for btn in buttons:
        if btn.layer == layer:
            btn.sync()


if __name__ == "__main__":
    engine = Engine()
    asm = engine.assignments
    mix = engine.mixer
    ctr = engine.controller

    mix.emit_parameters()
    setup_main_mix()

    engine.on(Engine.ChannelUnselected, on_channel_unselected)
    engine.on(Engine.ChannelSelected, on_channel_selected)
    engine.on(Engine.ChannelReselected, on_channel_reselected)
    engine.on(Engine.ChannelConfigModeChanged, on_chan_cfg_mode_changed)
    engine.on(Engine.LayerChanged, on_layer_change)

    ctr.on(ctr.EncoderPressed, on_encoder_short_pressed)
    ctr.on(ctr.EncoderLongPressed, on_encoder_long_pressed)

    engine.set_chan_cfg_mode(ChannelConfigMode.AuxSends)
