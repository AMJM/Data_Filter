import pandas as pd
import math as m
import matplotlib.pyplot as plt


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Velocity:
    def __init__(self, stop, dead_slow, slow, half, full):
        self.stop = stop
        self.dead_slow = dead_slow
        self.slow = slow
        self.half = half
        self.full = full

    def discrete_range(self):
        v0 = -self.full * 1.5
        v1 = -(self.half + self.full) / 2
        v2 = -(self.slow + self.half) / 2
        v3 = -(self.dead_slow + self.slow) / 2
        v4 = -(self.stop + self.dead_slow) / 2
        v5 = (self.stop + self.dead_slow) / 2
        v6 = (self.dead_slow + self.slow) / 2
        v7 = (self.slow + self.half) / 2
        v8 = (self.half + self.full) / 2
        v9 = self.full * 1.5
        return [v0, v1, v2, v3, v4, v5, v6, v7, v8, v9]

class Ship():
    def __init__(self, name, beam, height, length, velocity):
        self.name = name
        self.beam = beam
        self.height = height
        self.length = length
        self.velocity = velocity

    def discrete_velocity(self):
        return self.velocity.discrete_range()

    def calc_dist(self, center, angle, buoys, target):
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

        if direction == -1: # virado a bombordo
            sh_pb = front_pb
            sh_sb = back_sb
            section_pb = section_front
            section_sb = section_back
        else: # na direcao ou virado a estibordo
            sh_pb = back_pb
            sh_sb = front_sb
            section_pb = section_back
            section_sb = section_front

        dsb = self._dist_line_point(buoys[section_sb], buoys[section_sb+2], sh_sb) # distancia estibordo
        dpb = self._dist_line_point(buoys[section_pb+1], buoys[section_pb+3], sh_pb) # distancia bombordo
        dtg = self._dist_point_point(center, target) # distancia target

        return pd.Series([dpb, dsb, dtg])

    def _determine_section(self, point, buoys):
        for i in range(0, len(buoys), 2):
            if point.x < (buoys[len(buoys)-i-1].x + buoys[len(buoys)-i-2].x)/2:
                if len(buoys)-i-2 == len(buoys)-2:
                    return len(buoys) - i - 4 # Desconsidera se passa do target
                else:
                    return len(buoys) - i - 2

    def _determine_direction(self, section_front, angle, buoys):
        # -1 para bombordo, 0 na mesma direcao e 1 para estibordo
        ini = Point((buoys[section_front].x + buoys[section_front + 1].x)/2, (buoys[section_front].y + buoys[section_front + 1].y)/2)
        end = Point((buoys[section_front + 2].x + buoys[section_front + 3].x)/2, (buoys[section_front+2].y + buoys[section_front + 3].y)/2)
        line_angle = m.degrees(m.atan((end.y - ini.y)/(end.x - ini.x))) - 180
        if line_angle - angle > 0:
            return 1
        elif line_angle - angle == 0:
            return 0
        else:
            return -1


    def _dist_line_point(self, line_p_1, line_p_2, point):
        y_diff = line_p_2.y - line_p_1.y
        x_diff = line_p_2.x - line_p_1.x
        return abs(y_diff * point.x - x_diff * point.y + line_p_2.x * line_p_1.y - line_p_2.y * line_p_1.x) / m.sqrt(y_diff ** 2 + x_diff ** 2)

    def _dist_point_point(self, p1, p2):
        return m.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def main():
    dt_root = "C:/Users/AlphaCrucis_Control1/Dropbox/"
    dt_paths = ["Suape_2017/RT/", "Suape_Aframax/RT/", "Suape_PDZ/FT/Outputs_FT/", "Suape_PDZ/RT/", "Suape_PDZ/RT2/"]
    dt_path = "C:/Users/AlphaCrucis_Control1/Dropbox/Suape_2017/RT/Caso26/"
    dt_cases = ["casos.xlsx", "casos.xlsx", "casos_.xlsx", "casos.xlsx", "casos.xlsx"]
    dt_pos_path = "Caso" # Concatenar o numero do caso
    dt_num_case = [[1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 17, 18, 22, 23, 26, 28], # Suape_2017/RT
                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], # Suape_Aframax/RT
                   [1, 2, 3, 4], # Suape_PDZ/FT/Outputs_FT
                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19], # Suape_PDZ/RT
                   [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 19, 21]] # Suape_PDZ/RT2
    dt_file_dict = [{"Suezmax": "smh_v00004", "Conteneiro": "smh_v00077", "Aframax": "smh_v00036"}, # Caso 28 do Suape_2017 tratado com excecao smh_v00030.txt - Conteneiro
                    {"Aframax": "smh_v00036", "Suezmax": "smh_v00037"},
                    {}, # ***** PERGUNTAR QUAL PEGAR JA QUE TEM VARIOS *****
                    {}, # ***** NAVIO MENOR? APENAS 1 PROPULSOR *****
                    {}] # ***** COM PROPULSOR E SEM LEME? *****
    dt_file_extension = ".txt"

    for idx in range(0, len(dt_paths)):
        # Leitura da planilha de casos
        path_xlsx = dt_root + dt_paths[idx] + dt_cases[idx]
        print(path_xlsx)
        df_case = pd.read_excel(path_xlsx, sheet_name="Plan1")
        if not df_case[df_case["Caso"].isnull()].empty:
            end_idx = df_case[df_case["Caso"].isnull()].index.tolist()[0] - 1
            df_case = df_case.loc[0:end_idx]
        for num_case in dt_num_case[idx]:
            ship_fullname = df_case[df_case["Caso"] == num_case]["Navio"].to_string(index=False)
            ship_firstname = ship_fullname.split(' ', 1)[0]
            if idx == 0 and num_case == 28:
                file = "smh_v00030"
            elif idx > 1: # ***** VERIFICAR COMO TRATAR OS DADOS DO PDZ *****
                print("A implementar")
            else:
                file = dt_file_dict[idx].get(ship_firstname)
            path_case = dt_root + dt_paths[idx] + "Caso" + str(num_case) + "/" + file + dt_file_extension
            print(path_case)

    num_case = 1
    dt_filename = "smh_v00036.txt"
    vel_label = [-4, -3, -2, -1, 0, 1, 2, 3, 4] # 0 parado, 1 muito devagar, 2 devagar, 3 meia forca e 4 toda forca e seus respectivos opostos na outra direcao
    param = ["time_stamp", "x", "y", "zz", "vx", "vy", "vzz", "rudder_demanded_orientation_0", "propeller_demanded_rpm_0"]
    simul_data = ["Navio", "Cenário", "Manobra", "Corrente", "Vento", "Onda"]
    mult_param_data = {"Corrente": 2, "Vento": 2, "Onda": 3}

    ship = Ship("Aframax T150", 42, 22.5, 244.745, Velocity(0, 19.2, 38.4, 57.6, 76.8))
    buoys = [
        Point(11722.4553, 5583.4462),
        Point(11771.3626, 5379.2566),
        Point(9189.9177, 4969.4907),
        Point(9237.9939, 4765.5281),
        Point(6895.1451, 4417.3749),
        Point(6954.9285, 4225.9083),
        Point(5540.617, 4088.186),
        Point(5809.4056, 3767.7633)
    ]
    target = Point(5790.0505, 3944.9947)

    df = pd.read_csv(dt_path + dt_filename, escapechar="%", skiprows=2, delim_whitespace=True)
    df.rename(columns=lambda x: x.strip(), inplace=True)
    df = df[param]

    df_case = pd.read_excel("C:/Users/AlphaCrucis_Control1/Dropbox/Suape_2017/RT/casos.xlsx", sheet_name="Plan1")
    end_idx = df_case[df_case["Caso"].isnull()].index.tolist()[0] - 1
    df_case = df_case.loc[0:end_idx]
    #print(df_case)

    # Filtragem dos dados
    # Terceiro quadrante negativo para estar entrando no porto
    df.drop(df[df["zz"] > 0].index, inplace=True)
    # Estar no meio dos pontos extremos para estar dentro do canal
    x_ini = buoys[1].x
    y_ini = buoys[0].y
    x_end = target.x
    y_end = buoys[len(buoys)-1].y
    df.drop(df[((df["x"] > x_ini) | (df["y"] > y_ini) | (df["x"] < x_end) | (df["y"] < y_end))].index, inplace=True)

    df[["distance_port", "distance_starboard", "distance_target"]] = df.apply(lambda x : ship.calc_dist(Point(x["x"], x["y"]), x["zz"], buoys, target), axis=1)
    df["propeller_demanded_rpm_0"] = pd.cut(df["propeller_demanded_rpm_0"], ship.discrete_velocity(), right=False, labels=vel_label)
    df["propeller_demanded_rpm_0"] = df.apply(lambda x : int(x["propeller_demanded_rpm_0"]), axis=1)

    #plt.interactive(True)
    #df.plot(x='time_stamp', y='propeller_demanded_rpm_0')
    #plt.ioff()
    #plt.savefig("../Output/propeller.png")
    #plt.show()

    f = open("../Output/filter_smh_v00036.txt", "w+")
    for p in simul_data:
        check = mult_param_data.get(p)
        if check is None:
            f.write(p + ": " + df_case[df_case["Caso"] == num_case][p].to_string(index=False) + "\r\n")
        else:
            pos = df_case.columns.get_loc(p)
            f.write(p + ": ")
            for i in range(0, check):
                f.write(df_case[df_case["Caso"] == num_case].iloc[0, pos+i] + " ")
            f.write("\r\n")
    f.write("\r\n")
    f.close()

    df.to_csv("../Output/filter_smh_v00036.txt", mode='a', index=False, sep=' ')#, mode='a', index=False, sep=' ')


main()