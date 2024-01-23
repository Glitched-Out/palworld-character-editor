# Palworld character appearance editor

This is a script to change the appearance of your character without loosing progression
or anything else. It just changes the appearance!

> ⚠️Warning: This is an experimental script. Keep in mind that if the game gets an update this script could stop working. Always create a backup of your saves before executing.
>
> Tested on Palworld v0.1.2.0

## How to use

1. Locate the `.sav` file of the player that you want to change its appearance.

In order to do that, you can go to the screen where you can select the world (if it is a local world), select the world that contains the character, and click in the folder icon (bottom left corner).

This button will open the folder of the world. Then navigate to "Players" and select your player (if you're the host it will be "00000000000000000000000000000001.sav").

Copy the path of that file, we will need it later. For example: `C:\Users\user\AppData\Local\Pal\Saved\SaveGames\00000123456789000\1212FED144C69D0F3D57F2817389C369\Players\00000000000000000000000000000001.sav`.

This will be the <sav_with_desired_progression>.


2. Create a new world and create a new character with the desired appeareance.

Repeat the previous process to get the path of the character with the new appearance.

This will be the <sav_with_desired_appeareance>.

3. Execute the script file. It will require to have `python` installed.

`python palworld_change_appearance.py <sav_with_desired_appeareance> <sav_with_desired_progression>`

For example:
```bash
python palworld_change_appearance.py "C:\Users\....\Players\my_handsome_char.sav" "C:\Users\....\Players\my_strong_char.sav"
```

This will replace `my_strong_char.sav` with the desired character, but it will create a backup in `my_strong_char.sav.old`.
