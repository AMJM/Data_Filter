import pandas as pd
import math as m
import matplotlib.pyplot as plt
import re
import os

err_control = None

class P3D_file:
    def __init__(self, path):
        self.path = path

    def find_dimensions(self):
        global err_control
        regex = re.compile("VESSEL[\s\S\n]*?(?<=BEAM = )(\d+.\d+)[\s\S\n]*?(?<=HEIGHT = )(\d+.\d+)[\s\S\n]*?(?<=LENGTH = )(\d+.\d+)")
        p3d_file = open(self.path)
        dim = regex.findall(p3d_file.read())
        if len(dim[0]) != 3:
            err_control.eprint("Dimensoes da embarcacao nao encontradas")
            return [-1, -1, -1]
        else:
            beam = float(dim[0][0])
            height = float(dim[0][1])
            length = float(dim[0][2])
            return beam, height, length


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Velocity:
    def __init__(self, stop, dead_slow, slow, half, full, rdead_slow = 0, rslow = 0, rhalf = 0, rfull = 0):
        self.stop = stop
        self.dead_slow = dead_slow
        self.slow = slow
        self.half = half
        self.full = full
        self.rdead_slow = rdead_slow if rdead_slow < dead_slow else -dead_slow
        self.rslow = rslow if rslow < slow else -slow
        self.rhalf = rhalf if rhalf < half else -half
        self.rfull = rfull if rfull < full else -full

    def discrete_range(self):
        # *************** Para fazer o teste, os limites estao grandes, mas e melhor usar fator 1.5 ***********************
        factor = 150
        v0 = self.rfull * factor
        v1 = (self.rhalf + self.rfull) / 2
        v2 = (self.rslow + self.rhalf) / 2
        v3 = (self.rdead_slow + self.rslow) / 2
        v4 = (self.stop + self.rdead_slow) / 2
        v5 = (self.stop + self.dead_slow) / 2
        v6 = (self.dead_slow + self.slow) / 2
        v7 = (self.slow + self.half) / 2
        v8 = (self.half + self.full) / 2
        v9 = self.full * factor
        return [v0, v1, v2, v3, v4, v5, v6, v7, v8, v9]

    def discrete_value(self, idx):
        global err_control
        if abs(idx) == 0:
            val = self.stop
        elif abs(idx) == 1:
            val = self.dead_slow
        elif abs(idx) == 2:
            val = self.slow
        elif abs(idx) == 3:
            val = self.half
        elif abs(idx) == 4:
            val = self.full
        else:
            err_control.eprint("Velocidade discretizada incoerente")

        if idx < 0:
            val = -val
        return val


class Ship():
    def __init__(self, name, dim, velocity):
        self.name = name
        self.beam = dim[0]
        self.height = dim[1]
        self.length = dim[2]
        self.velocity = velocity

    def discrete_velocity(self):
        return self.velocity.discrete_range()

    def corresp_vel(self, idx):
        return self.velocity.discrete_value(idx)

    def calc_dist(self, center, angle, buoys, target):
        global err_control
        # Coordenadas medias frontal e traseira
        front = Point(center.x + self.length / 2 * m.cos(m.radians(angle)), center.y + self.beam / 2 * m.sin(m.radians(angle)))
        back = Point(center.x - self.length / 2 * m.cos(m.radians(angle)), center.y - self.beam / 2 * m.sin(m.radians(angle)))
        front_sb = Point(center.x + self.length / 2 * m.cos(m.radians(angle)) + self.beam / 2 * m.sin(m.radians(angle)), center.y + self.length / 2 * m.sin(m.radians(angle)) - self.beam / 2 * m.cos(m.radians(angle)))
        front_pb = Point(center.x + self.length / 2 * m.cos(m.radians(angle)) - self.beam / 2 * m.sin(m.radians(angle)), center.y + self.length / 2 * m.sin(m.radians(angle)) + self.beam / 2 * m.cos(m.radians(angle)))
        back_sb = Point(center.x - self.length / 2 * m.cos(m.radians(angle)) + self.beam / 2 * m.sin(m.radians(angle)), center.y - self.length / 2 * m.sin(m.radians(angle)) - self.beam / 2 * m.cos(m.radians(angle)))
        back_pb = Point(center.x - self.length / 2 * m.cos(m.radians(angle)) - self.beam / 2 * m.sin(m.radians(angle)), center.y - self.length / 2 * m.sin(m.radians(angle)) + self.beam / 2 * m.cos(m.radians(angle)))

        section_front = self._determine_section(front, buoys)
        section_back = self._determine_section(back, buoys)

        direction = self._determine_direction(section_front, angle, buoys)

        if direction == -1:  # virado a bombordo
            sh_pb = front_pb
            sh_sb = back_sb
            section_pb = section_front
            section_sb = section_back
        else:  # na direcao ou virado a estibordo
            sh_pb = back_pb
            sh_sb = front_sb
            section_pb = section_back
            section_sb = section_front
        dsb = self._dist_line_point(buoys[section_sb], buoys[section_sb + 2], sh_sb, -1)  # distancia estibordo
        dpb = self._dist_line_point(buoys[section_pb + 1], buoys[section_pb + 3], sh_pb, 1)  # distancia bombordo
        dtg = self._dist_point_point(center, target)  # distancia target

        if ~((angle % 360 > 135) and (angle % 360 < 315)):
            err_control.eprint("Direcao da embarcacao em saida")

        return pd.Series([dpb, dsb, dtg])

    def _determine_section(self, point, buoys):
        for i in range(0, len(buoys), 2):
            if point.x < (buoys[len(buoys) - i - 1].x + buoys[len(buoys) - i - 2].x) / 2:
                if len(buoys) - i - 2 == len(buoys) - 2:
                    return len(buoys) - i - 4  # Desconsidera se passa do target
                else:
                    return len(buoys) - i - 2
        return len(buoys) - i - 2

    def _determine_direction(self, section_front, angle, buoys):
        # -1 para bombordo, 0 na mesma direcao e 1 para estibordo
        ini = Point((buoys[section_front].x + buoys[section_front + 1].x) / 2, (buoys[section_front].y + buoys[section_front + 1].y) / 2)
        end = Point((buoys[section_front + 2].x + buoys[section_front + 3].x) / 2, (buoys[section_front + 2].y + buoys[section_front + 3].y) / 2)
        line_angle = m.degrees(m.atan((end.y - ini.y) / (end.x - ini.x))) - 180

        if line_angle - angle > 0:
            return 1
        elif line_angle - angle == 0:
            return 0
        else:
            return -1

    def _dist_line_point(self, line_p_1, line_p_2, point, type):
        # type 1 bombordo e -1 estibordo
        y_diff = line_p_2.y - line_p_1.y
        x_diff = line_p_2.x - line_p_1.x

        factor = 1
        y_line = y_diff / x_diff * (point.x - line_p_1.x) + line_p_1.y
        if (y_line > point.y and type == 1) or (y_line < point.y and type == -1):
            factor = -1

        return factor * abs(y_diff * point.x - x_diff * point.y + line_p_2.x * line_p_1.y - line_p_2.y * line_p_1.x) / m.sqrt(y_diff ** 2 + x_diff ** 2)

    def _dist_point_point(self, p1, p2):
        return m.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


class ErrorPrint:
    def __init__(self):
        self.count_error = 0
        self.global_error = 0

    def eprint(self, text):
        print("\t\t*** ERRO: " + text + " ***")
        self.count_error = self.count_error + 1
        self.global_error = self.global_error + 1

    def reset(self):
        self.count_error = 0

    def get_num_error(self):
        return self.count_error

    def get_num_global_error(self):
        return self.global_error


def main():
    # Para adicionar nova pasta do dropbox: adicionar o diretorio dos casos em dt_paths, o nome do arquivo com as informacoes dos casos em dt_cases,
    # uma lista dos casos a serem testados em dt_num_case e os arquivos de leitura de cada caso em dt_file_dict
    # Verificar tambem se sera necessario alterar o nome das colunas em param, adicionar velocidades de embarcacoes em ship_velocity e o ponto das boias e do target em list_buoys e list_target
    dt_root = "C:/Users/AlphaCrucis_Control1/Dropbox/"
    dt_paths = ["Suape_2017/RT/", "Suape_Aframax/RT/", "Suape_PDZ/FT/Outputs_FT/", "Suape_PDZ/RT/", "Suape_PDZ/RT2/"]
    dt_cases = ["casos.xlsx", "casos.xlsx", "casos_.xlsx", "casos.xlsx", "casos.xlsx"]
    dt_pos_path = "Caso"  # Concatenar o numero do caso
    dt_num_case = [[1, 2, 3, 4, 5, 6, 9, 10, 12, 13, 14, 17, 18, 22, 23, 26, 28],  # Suape_2017/RT
                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],  # Suape_Aframax/RT
                   [1, 2, 3, 4],  # Suape_PDZ/FT/Outputs_FT
                   [1, 2, 3, 4, 5, 6, 7, 9, 12, 13, 14, 15, 16, 17],  # Suape_PDZ/RT
                   [1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 19]]  # Suape_PDZ/RT2
    dt_file_dict = [{"Suezmax": "smh_v00004", "Conteneiro": "smh_v00077", "Aframax": "smh_v00036"},  # Caso 28 do Suape_2017 tratado com excecao smh_v00030.txt - Conteneiro
                    {"Aframax": "smh_v00036", "Suezmax": "smh_v00037"},
                    {1: "smh_v00004_20170814_102039", 2: "smh_v00004_20170814_103220", 3: "smh_v00004_20170814_114251", 4: "smh_v00004_20170816_175923"},
                    {1: "smh_v00037_20171009_093846", 2: "smh_v00037_20171009_101104", 3: "smh_v00037_20171009_104723", 4: "smh_v00037_20171009_112202", 5: "smh_v00028_20171009_135920", 6: "smh_v00028_20171009_154051",
                     7: "smh_v00028_20171009_170521", 9: "smh_v00053_20171010_081234", 12: "smh_v00030_20171010_110500", 13: "smh_v00030_20171010_134312", 14: "smh_v00072_20171010_150159",
                     15: "smh_v00072_20171010_154827", 16: "smh_v00025_20171010_165913", 17: "smh_v00025_20171010_181407"},
                    {1: "smh_v00037_20171218_093301", 2: "smh_v00037_20171218_104020", 3: "smh_v00028_20171218_115245", 4: "smh_v00028_20171218_135301", 5: "smh_v00028_20171218_144630", 6: "smh_v00053_20171218_155203",
                     8: "smh_v00053_20171219_091526", 9: "smh_v00030_20171219_100258", 11: "smh_v00030_20171219_111047", 12: "smh_v00030_20171219_132445", 19: "smh_v00030_20171220_105159"}]
    dt_file_extension = ".txt"
    dt_out_path = "../Output/"

    vel_label = [-4, -3, -2, -1, 0, 1, 2, 3, 4]  # 0 parado, 1 muito devagar, 2 devagar, 3 meia forca e 4 toda forca e seus respectivos opostos na outra direcao
    param = [["time_stamp", "x", "y", "zz", "vx", "vy", "vzz", "rudder_demanded_orientation_0", "propeller_demanded_rpm_0"],
             ["time_stamp", "x", "y", "zz", "vx", "vy", "vzz", "rudder_demanded_orientation_0", "propeller_demanded_0"]]
    simul_data = ["Navio", "Cenário", "Manobra", "Corrente", "Vento", "Onda"]
    mult_param_data = {"Corrente": 2, "Vento": 2, "Onda": 3}
    ship_velocity_rpm = {"Aframax": Velocity(0, 19.2, 38.4, 57.6, 76.8),
                         "Suezmax": Velocity(0, 28.77, 32.88, 57.54, 65.76),
                         "Conteneiro 336B48": Velocity(0, 31.92, 39.9, 55.86, 63.84),
                         "Conteneiro L366B51": Velocity(0, 20.4, 40.8, 61.2, 81.6),
                         "Capesize": Velocity(0, 27.18, 45.3, 63.42, 81.54),
                         "Capsan L333B48T14.3": Velocity(0, 31.92, 39.9, 55.86, 63.84),  # Novo - igual Conteneiro 336B48
                         "NewPanamax L366B49T15.2": Velocity(0, 20.4, 40.8, 61.2, 81.6),  # Novo - igual Conteneiro L366B51
                         }
    ship_velocity_kn = {"Aframax": Velocity(0, 203.09, 564.14, 1105.71, 1827.8, -121.85, -338.48, -663.42, -1096.68)}

    list_buoys = [[Point(11722.4553, 5583.4462), Point(11771.3626, 5379.2566), Point(9189.9177, 4969.4907), Point(9237.9939, 4765.5281),
                   Point(6895.1451, 4417.3749), Point(6954.9285, 4225.9083), Point(5540.617, 4088.186), Point(5809.4056, 3767.7633)],
                  [Point(11722.4553, 5583.4462), Point(11771.3626, 5379.2566), Point(9189.9177, 4969.4907), Point(9237.9939, 4765.5281),
                   Point(6895.1451, 4417.3749), Point(6954.9285, 4225.9083), Point(5540.617, 4088.186), Point(5809.4056, 3767.7633)],
                  [Point(11722.3589, 5583.1258), Point(11771.2493, 5379.1717), Point(9116.9042, 4962.0775), Point(9182.1188, 4746.3356),
                   Point(6843.3548, 4413.4023), Point(6932.4013, 4209.7791)],
                  [Point(11694.9971, 5591.3703), Point(11761.3162, 5347.1197), Point(9127.6203, 4943.6262), Point(9189.0030, 4698.5468),
                   Point(7175.8933, 4447.2715), Point(7220.9278, 4202.2184)],
                  [Point(11709.5909, 5544.3389), Point(11753.9045, 5340.5588), Point(9678.4495, 5060.9246), Point(9726.6952, 4851.4281),
                   Point(8044.8985, 4665.5996), Point(8085.7122, 4459.2627), Point(7173.0433, 4497.6472), Point(7235.8574, 4256.0789)],
                  ]
    list_target = [Point(5790.0505, 3944.9947),
                   Point(5790.0505, 3944.9947),
                   Point(6889.7808, 4312.0526),
                   Point(7200.3366, 4321.1497),
                   Point(7213.6943, 4380.5586)]
    global err_control
    err_control = ErrorPrint()

    for idx in range(0, len(dt_paths)):
        # Leitura da planilha de casos
        path_xlsx = dt_root + dt_paths[idx] + dt_cases[idx]
        print("Executando na pasta " + dt_paths[idx] + ":")
        try:
            df_case = pd.read_excel(path_xlsx, sheet_name="Plan1")
        except:
            err_control.eprint("Planilha de casos nao encontrada")

        # Limpeza dos dados para obter apenas casos existentes
        if not df_case[df_case["Caso"].isnull()].empty:
            end_idx = df_case[df_case["Caso"].isnull()].index.tolist()[0] - 1
            df_case = df_case.loc[0:end_idx]

        # Itera pelos casos selecionados em cada pasta
        for num_case in dt_num_case[idx]:
            err_control.reset()
            print("\tGerando caso " + str(num_case) + "...")

            # Obtem os arquivos de dados com os dados da manobra
            ship_fullname = df_case[df_case["Caso"] == num_case]["Navio"].to_string(index=False)
            ship_firstname = ship_fullname.split(' ', 1)[0]
            if dt_paths[idx] == "Suape_2017/RT/" and num_case == 28:  # Especial pois nao bate com o nome do navio
                file = "smh_v00030"
            elif dt_paths[idx] == "Suape_PDZ/FT/Outputs_FT/" or dt_paths[idx] == "Suape_PDZ/RT/" or dt_paths[idx] == "Suape_PDZ/RT2/":  # Casos PDZ
                file = dt_file_dict[idx].get(num_case)
            else:  # Casos nao PDZ
                file = dt_file_dict[idx].get(ship_firstname)
            path_case = dt_root + dt_paths[idx] + dt_pos_path + str(num_case) + "/" + file + dt_file_extension
            df = pd.read_csv(path_case, escapechar="%", skiprows=2, delim_whitespace=True)
            df.rename(columns=lambda x: x.strip(), inplace=True)

            if dt_paths[idx] == "Suape_Aframax/RT/":
                real_param = param[1]
            else:
                real_param = param[0]
            df = df[real_param]

            # ***** Implementar selecao de boias e target *****
            if len(list_buoys) - 1 < idx:
                err_control.eprint("Posicao das boias inexistente")
            else:
                buoys = list_buoys[idx]
            if len(list_target) - 1 < idx:
                err_control.eprint("Posicao do target inexistente")
            else:
                target = list_target[idx]

            # Procura as dimensoes do navio no p3d
            list_paths = []
            for filep3d in os.listdir(dt_root + dt_paths[idx] + dt_pos_path + str(num_case)):
                if filep3d.endswith(".p3d"):
                    list_paths.append(os.path.join(dt_root + dt_paths[idx] + dt_pos_path + str(num_case), filep3d))
            if len(list_paths) > 1:
                err_control.eprint("Multiplicidade de P3D")
            ship_dim = P3D_file(list_paths[len(list_paths)-1]).find_dimensions()  # Usa o ultimo P3D caso tenha multiplicidade

            # Cria o navio do teste
            if real_param[8] == "propeller_demanded_rpm_0":
                ship_velocity = ship_velocity_rpm
            elif real_param[8] == "propeller_demanded_0":
                ship_velocity = ship_velocity_kn
            else:
                err_control("Parametro de velocidade nao definido")
            vel = ship_velocity.get(ship_firstname)
            if vel is None:
                vel = ship_velocity.get(ship_fullname)
                if vel is None:
                    err_control.eprint("Navio nao possui velocidade registrada - " + ship_fullname)
                    vel = ship_velocity.get("Aframax")  # ************* REMOVER ISSO DEPOIS ****************
            ship = Ship(ship_fullname, ship_dim, vel)  # ***** Talvez seja melhor mudar para fullname dependendo se o nome precisa bater inteiro ou nao *****

            # Filtragem dos dados
            # Terceiro quadrante negativo para estar entrando no porto
            df = df[((df["zz"] % 360 > 135) & (df["zz"] % 360 < 315))]
            # Estar no meio dos pontos extremos para estar dentro do canal
            x_ini = buoys[1].x - ship.length / 2
            y_ini = buoys[0].y
            x_end = target.x
            y_end = buoys[len(buoys) - 1].y
            df.drop(df[((df["x"] > x_ini) | (df["y"] > y_ini) | (df["x"] < x_end) | (df["y"] < y_end))].index, inplace=True)

            # Calcula as distancias e discretiza a velocidade
            df[["distance_port", "distance_starboard", "distance_target"]] = df.apply(lambda x: ship.calc_dist(Point(x["x"], x["y"]), x["zz"], buoys, target), axis=1)
            df["original_propeller"] = df[real_param[8]]
            df[real_param[8]] = pd.cut(df[real_param[8]], ship.discrete_velocity(), right=False, labels=vel_label)
            df[real_param[8]] = df.apply(lambda x: int(x[real_param[8]]), axis=1)
            df["discrete_propeller"] = df.apply(lambda x: ship.corresp_vel(x[real_param[8]]), axis=1)
            df = df.round({"distance_port": 3, "distance_starboard": 3, "distance_target": 3})

            # Gera a saida
            if not os.path.exists(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case)):
                os.makedirs(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case))
            f = open(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/" + file + dt_file_extension, "w+")
            for p in simul_data:
                check = mult_param_data.get(p)
                if check is None:
                    f.write(p + ": " + df_case[df_case["Caso"] == num_case][p].to_string(index=False) + "\r\n")
                else:
                    pos = df_case.columns.get_loc(p)
                    f.write(p + ": ")
                    for i in range(0, check):
                        f.write(df_case[df_case["Caso"] == num_case].iloc[0, pos + i] + " ")
                    f.write("\r\n")
            f.write("\r\n")
            f.close()

            # plt.interactive(True)
            df.plot(x='time_stamp', y=real_param[8])
            # plt.ioff()
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/propeller.png")
            # plt.show()
            df.plot(x='time_stamp', y='distance_port')
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/dist_port.png")
            df.plot(x='time_stamp', y='distance_starboard')
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/dist_star.png")
            df.plot(x='time_stamp', y='distance_target')
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/dist_target.png")
            df.plot(x='time_stamp', y='rudder_demanded_orientation_0')
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/rudder.png")
            ax = df.plot(x='time_stamp', y='original_propeller')
            df.plot(x='time_stamp', y='discrete_propeller', ax=ax)
            plt.savefig(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/original_discrete_propeller.png")
            plt.close("all")

            df.to_csv(dt_out_path + dt_paths[idx] + dt_pos_path + str(num_case) + "/" + file + dt_file_extension, mode='a', index=False, sep=' ')  # , mode='a', index=False, sep=' ')

            if err_control.get_num_error() == 0:
                print("\t\tOK: Sem erro de execucao")
            else:
                print("\t\tDiretorio do teste: " + dt_root + dt_paths[idx] + dt_pos_path + str(num_case))

    print("\n*** Processamento concluido! ***")
    print("Quantidade total de erros encontrados: " + str(err_control.get_num_global_error()))



main()

#################################################################
# Codigo auxiliar no matlab para comparar a posicao das boias
# i=1
# sceneConfig(i,'Dome')
# load(strcat('.\Caso',num2str(i),'\cases.mat'))
# for i = 1:11
# if def_buoy(i).x ~= buoy(i).x || def_buoy(i).y ~= buoy(i).y
# disp('ERRO')
# end
# end
#
# Na primeira: def_buoy = buoy
#################################################################
