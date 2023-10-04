import bpy, re, ast
import os, csv, codecs #辞書

# 設定
def preference():
	preference = bpy.context.preferences.addons[__name__.partition('.')[0]].preferences

	return preference


# 翻訳辞書の取得
def GetTranslationDict():
	dict = {}
	path = os.path.join(os.path.dirname(__file__), "translation_dictionary.csv")

	with codecs.open(path, 'r', 'utf-8') as f:
		reader = csv.reader(f)
		dict['ja_JP'] = {}
		for row in reader:
			if row:
				for context in bpy.app.translations.contexts:
					dict['ja_JP'][(context, row[1].replace('\\n', '\n'))] = row[0].replace('\\n', '\n')

	return dict


# フォルダー内のシェイプキーブロックを返す
def get_folder_innner_sk_list(tgt_folder_index, sk_data):
	sk_bl = sk_data.key_blocks
	sk_l = []


	for i,sk in enumerate(sk_bl):
		if tgt_folder_index < i: # 対象フォルダーより多いインデックス
			if is_folder(sk): # 次のフォルダーに当たったら終了する
				break
			sk_l += [sk.name]


	# print(sk_l,  8888888888888)

	return sk_l


# 所属しているフォルダーを返す
def get_affiliation_folder(tgt_sk,index, sk_bl):
	if is_folder(tgt_sk):
		return

	is_top = False

	sk_l = [(i,sk) for i,sk in enumerate(sk_bl)]
	for i,sk in reversed(sk_l):  # リストの逆から検索する
		if tgt_sk == sk: # アクティブのシェイプキー以降
			is_top = True
			continue

		if not is_top:
			continue

		if is_folder(sk):
			return sk

	return


# 指定名の対象オブジェクトを取得
def get_target_obj(obj_name):
	obj = bpy.context.object
	if obj_name:
		if obj_name in bpy.data.objects:
			obj = bpy.data.objects[obj_name]

	return obj


# シェイプキーがフォルダーかどうかを調べる
def is_folder(sk):
	return "folder:" in sk.vertex_group


def convert_mini_text_to_dic(text):
	dic = {}
	text_l= text.split(",")
	for i in text_l:
		dic[i.split(":")[0]] = int(i.split(":")[1])

	return dic


# 辞書テキストの不要な文字を除去する
def convert_dic_to_mini_text(dic):
	text = str(dic).replace(" ","")
	text = text.replace("{","")
	text = text.replace("}","")
	text = text.replace("'","")
	return text


# シェイプキーのキーフレームの有無をチェックする
def check_use_keyframe(sks, name_l):
	sc = bpy.context.scene
	use_cur_key_l = []
	is_remove = False

	re_compile = re.compile('key_blocks\[\"(.+)\"\].value')
	if sks.animation_data:
		if sks.animation_data.action:
			for fc in sks.animation_data.action.fcurves:
				matches = re_compile.findall(fc.data_path)
				if matches:
					if matches[0] in name_l:
						for ky in fc.keyframe_points:
							if int(ky.co[0]) == sc.frame_current:
								use_cur_key_l += [fc.data_path]
								continue


	if len(name_l) == len(use_cur_key_l):
		is_remove = True

	return use_cur_key_l, is_remove


# 操作履歴にアクセス
def Get_just_before_history():
	w_m = bpy.context.window_manager
	old_clipboard = w_m.clipboard

	win = w_m.windows[0]
	area = win.screen.areas[0]
	area_type = area.type
	area.type = "INFO"
	override = bpy.context.copy()
	override['window'] = win
	override['screen'] = win.screen
	override['area'] = win.screen.areas[0]
	bpy.ops.info.select_all(override, action='SELECT')
	bpy.ops.info.report_copy(override)
	bpy.ops.info.select_all(override, action='DESELECT')
	area.type = area_type
	clipboard = w_m.clipboard
	if not clipboard:
		return ""
	clipboard = clipboard.split("\n")


	w_m.clipboard = old_clipboard
	return clipboard


# メッシュと関連付けられているポーズオブジェクトを取得
def get_bind_pose_obj(mesh_obj):
	tgt_obj_l = []
	if mesh_obj.type == "MESH":
		for m in mesh_obj.modifiers:
			if m.type == "ARMATURE":
				if m.object:
					tgt_obj_l += [m.object]

	return tgt_obj_l


# ポーズと関連付けられているメッシュオブジェクトを取得
def get_bind_mesh_obj(pose_obj):
	tgt_obj_l = [chi for chi in pose_obj.children
	if chi.hide_viewport == False
	if chi.hide_get() == False
	if chi.type == "MESH"
	for m in chi.modifiers
	if m.type == "ARMATURE"
	if m.object == pose_obj
	]

	return tgt_obj_l


# 一括設定用の選択インデックスを取得
def get_sk_batch_index(sk_pr):
	select_l = sk_pr.multi_select_data
	if select_l:
		select_l = ast.literal_eval(select_l)

	return select_l
