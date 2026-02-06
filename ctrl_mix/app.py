from ctrl_mix.core.engine import ChannelConfigMode, Engine
from ctrl_mix.motu.channel import MotuAuxSendCapable, MotuGroupSendCapable, MotuMainSendCapable
from ctrl_mix.xtouch.control import Encoder


class ConfigModeHandler:
    @staticmethod
    def prepare():
        layer = engine.state.layer
        encs = ctr.side_encoders[layer]
        ch_idx = engine.state.selected_channel[layer]
        chan = mix.main if ch_idx == -1 else asm.main_mix[ch_idx].channel

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

        elif chan is mix.main:
            # Main aux => Side encoders
            engine.assign_encoders(False, engine.get_main_aux_sends())


class EqModeHandler(ConfigModeHandler):
    @staticmethod
    def enter():
        layer, chan, encs = EqModeHandler.prepare()

        for i, band in enumerate(chan.eq.get_bands()):
            enc_a = encs[i * 2]
            enc_b = encs[i * 2 + 1]
            EqModeHandler.update_band(enc_a, enc_b, band)

    @staticmethod
    def update_band(enc_a, enc_b, band):
        on = band.enable.normalized

        engine.assign(enc_a, band.gain, on)
        engine.assign(enc_b, band.freq, on)

        enc_a.is_enabled = band.enable.normalized
        enc_b.is_enabled = band.enable.normalized

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
        layer, chan, encs = EqModeHandler.prepare()
        band = chan.eq.get_bands()[encoder.index % 8 // 2]
        mix.set_parameter(band.enable, 1 - band.enable.value)
        enc_b = encs[encs.index(encoder) + 1]
        EqModeHandler.update_band(encoder, enc_b, band)


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

        # Main send => Top encoder
        if isinstance(strip.channel, MotuMainSendCapable):
            engine.assign(encoder, strip.channel.main_send)

        # Channel strip fader => Fader
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
    chan = asm.main_mix[ch].channel
    mode_map[engine.state.chan_cfg_mode].enter()

    # Group sends => Channel encoders
    if isinstance(chan, MotuGroupSendCapable):
        engine.assign_encoders(True, engine.get_group_sends(chan), layer)

    # Main send => Last channel encoder
    if isinstance(chan, MotuMainSendCapable):
        engine.assign(ctr.channel_encoders[layer * 8 + 7], chan.main_send)


def on_channel_unselected(layer: int, prev_ch: int):
    setup_main_mix()


def on_channel_reselected(layer: int, prev_ch: int):
    ...


if __name__ == "__main__":
    engine = Engine()
    asm = engine.assignments
    mix = engine.mixer
    ctr = engine.controller

    mix.sync_to_store()
    setup_main_mix()

    engine.on(Engine.ChannelUnselected, on_channel_unselected)
    engine.on(Engine.ChannelSelected, on_channel_selected)
    engine.on(Engine.ChannelReselected, on_channel_reselected)
    engine.on(Engine.ChannelConfigModeChanged, on_chan_cfg_mode_changed)

    ctr.on(ctr.EncoderPressed, on_encoder_short_pressed)
    ctr.on(ctr.EncoderLongPressed, on_encoder_long_pressed)

    engine.set_chan_cfg_mode(ChannelConfigMode.EQ)
    engine.select_channel(0, 6)
