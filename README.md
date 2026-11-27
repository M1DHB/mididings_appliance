# mididings_appliance
A mididings appliance running on a minimal Debian install on AMD Thin Client Hardware.

My use case is to use mididings to initiate and decode Line 6 PODxt Patch Dumps and route selected CCs to a Midi Captain foot
controller running [Midi Captain MAX](https://github.com/MC-Music-Workshop/midi-captain-max) firmware.
The Midi Captain follows the PODxt and [pod-ui](https://github.com/arteme/pod-ui) when the Patch is changed.

I decided to use a dedicated headless linux box because I'm using Windows for my setup and mididings is only available on linux.
I run [pod-ui](https://github.com/arteme/pod-ui) on Windows 11 (my DAW and everything else is on W11) and connect to the Linux box with rtp-midi over my LAN.

I use different midings scenes to setup the routing and decoding depending on how things are connected. (The PODxt output on USB echoes CC and PC messages but not on DIN)

Re Hardware: The PODxt and the Midi Captain midi can both connect via USB or 5 pin DIN. I prefer to use 5 PIN din and so in my case I have added a USB Midi interface (CME H4MIDI).
Its not really necessary but one of my PODxt's has a faulty USB port.

The applianceDebug.py file is a very rough working version. It's not tidy at all and has debug bits left in.
It might be a useful framework for other mididings applications.

I plan to add detailed steps for setting up the thin client, installing mididings under uv and details of the hardware.

# I had lots of assistance:

The Line 6 PODxt patch dump decoding came from Arteme, see : [pod-ui Patch Data](https://github.com/arteme/pod-ui/issues/83)

Stefets helped me get mididings working, see:  [mididings minimal install](https://github.com/mididings/mididings/issues/43)

# Thanks to you both.

Google helped me untangle my rubbish Python code :)


I have a GUI using [NiceGUI](https://nicegui.io/) to control mididings scenes and also switch Midi Captain Pages.


<img width="396" height="769" alt="NiceDings" src="https://github.com/user-attachments/assets/0e8f13d7-4cb5-4345-be66-05d4d342454b" />

