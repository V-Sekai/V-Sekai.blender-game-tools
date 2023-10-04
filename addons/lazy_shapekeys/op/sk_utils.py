import bpy


# ドライバーをミュートにする
def mute_shapekey_driver(skeys):
	if skeys.animation_data:
	    devs = skeys.animation_data.drivers
	    if devs:
	        for k_block in skeys.key_blocks:
	            for dv in devs:
	                if ('key_blocks["%s"].value' % k_block.name) == dv.data_path:
	                    dv.mute = True


# 親のキーを有効化する
def set_parent_key_value(keyblks,tgt_sk):
	tgt_sk.relative_key.value = 1
	if tgt_sk.relative_key == keyblks[0]:
		return
	if tgt_sk.relative_key.name == "Basis":
		return
	return set_parent_key_value(keyblks,tgt_sk.relative_key)
