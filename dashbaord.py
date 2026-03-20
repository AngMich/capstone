import pandas as pd
import joblib
import os
import streamlit as st


def collect_inputs():
    st.title('Energy Efficiency Strategy Room')
    st.write('welcome to the energy efficiency strategy room:')
    st.write('you will be given some input choices for the data center configuration')

    workload = float(st.number_input("Enter Server Workload %:", value=10.0, step=5.0))
    inlet_temp = float(st.number_input("Enter Inlet Temperature Setpoint °C:", value=15.0, step=0.5))

    at = st.selectbox(
        "Ambient temperature input mode",
        options=[1, 2],
        format_func=lambda x: "seasonal testing" if x == 1 else "manual testing"
    )

    if at == 1:
        ambient_temp_choice = st.selectbox(
            "Ambient temperature input mode",
            options=[1, 2, 3, 4],
            format_func=lambda x: {
                1: "FALL",
                2: "WINTER",
                3: "SPRING",
                4: "SUMMER"
            }
            [x]
        )
        if ambient_temp_choice == 1:
            ambient_temp = 19.7
        elif ambient_temp_choice == 2:
            ambient_temp = 10.7
        elif ambient_temp_choice == 3:
            ambient_temp = 16.7
        elif ambient_temp_choice == 4:
            ambient_temp = 28
    elif at == 2:
        ambient_temp = float(st.number_input("Enter Ambient (Outside) Temperature °C:", value=0.0, step=0.5))
        if ambient_temp > 57:
            ambient_temp = float(
                st.number_input("Ambient temperature is too high try less than 57:", value=57.0, step=0.5))

    s = st.selectbox(
        "Enter Cooling Strategy:",
        options=[1, 2, 3, 4, 5],
        format_func=lambda x: {
            1: "Boost All",
            2: "Eco Mode",
            3: "Increase Chiller",
            4: "Maintain",
            5: "Reduce AHU"
        }[x]
    )
    strategies = {1: 'Boost All', 2: 'Eco Mode', 3: 'Increase Chiller', 4: 'Maintain', 5: 'Reduce AHU'}
    strategy = strategies.get(s)

    return workload, inlet_temp, ambient_temp, s ,strategy

def get_predictions(workload, inlet_temp, ambient_temp, strategy):
    saved_data = pd.DataFrame({
        'Server_Workload(%)': [workload],
        'Inlet_Temperature(°C)': [inlet_temp],
        'Ambient_Temperature(°C)': [ambient_temp],
        'Cooling_Strategy_Action': [strategy],
    })

    script_dir = os.path.dirname(os.path.abspath(__file__))

    cooling_model = joblib.load(os.path.join(script_dir, 'final_ridge_model_cooling.pkl'))
    outlook_model_09 = joblib.load(os.path.join(script_dir, 'final_quantile_model_outlook_09.pkl'))
    outlook_model_01 = joblib.load(os.path.join(script_dir, 'final_quantile_model_outlook_01.pkl'))
    outlook_model_05 = joblib.load(os.path.join(script_dir, 'final_quantile_model_outlook_05.pkl'))

    cooling_pred = cooling_model.predict(saved_data)[0]
    outlook_pred_01 = outlook_model_01.predict(saved_data)[0]
    outlook_pred_05 = outlook_model_05.predict(saved_data)[0]
    outlook_pred_09 = outlook_model_09.predict(saved_data)[0]

    return cooling_pred, outlook_pred_01, outlook_pred_05, outlook_pred_09

def results(workload, inlet_temp, s, cooling_pred, outlook_pred_01, outlook_pred_05, outlook_pred_09):
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.subheader('EFFICIENCY')
            cooling = (cooling_pred).round(2)
            st.write('predicted cooling power per rack', cooling, 'KW')
            PUE = (((3.0 * (workload / 100)) + cooling) / (3.0 * (workload / 100))).round(3)
            st.write("expected PUE is ", PUE)
    with col2:
        with st.container(border=True):
            st.subheader('COST ESTIMATION PER RACK')
            if s == 1:
                rate = 0.0855
            elif s == 2:
                rate = 0.0890
            elif s == 3:
                rate = 0.0880
            elif s == 4:
                rate = 0.0871
            elif s == 5:
                rate = 0.0875

            st.write("total cost is $", round((3.0 * (workload / 100) + cooling) * rate, 2), "per hour")
            st.write("total IT power cost is $", round((3.0 * (workload / 100)) * rate, 2), "per hour")
            st.write("added cooling cost is $", round((cooling) * rate, 2), "per hour")

            st.write("total cost is $", round(((3.0 * (workload / 100) + cooling) * rate) * 24, 2), "per day")
            st.write("total IT power cost is $", round(((3.0 * (workload / 100)) * rate) * 24, 2), "per day")
            st.write("added cooling cost is $", round(((cooling) * rate) * 24, 2), "per day")
    with col3:
        with st.container(border=True):
            st.subheader('STABILITY METRIC')
            ur = (outlook_pred_09 - outlook_pred_01).round(2)
            st.write(
                (outlook_pred_05).round(2), ' with an uncertainty range of', ur,
                'with a positive uncertainty or +', (outlook_pred_09 - outlook_pred_05).round(2),
                'and a negative of -', (outlook_pred_05 - outlook_pred_01).round(2)
            )
            if PUE < 1.5:
                if ur > 5:
                    dt = (outlook_pred_05 - inlet_temp)
                    st.write(
                        "expected DT is around:", dt.round(2), 'with a positive uncertainty or +',
                        ((outlook_pred_09 - outlook_pred_05) + dt).round(2), 'and a negative of -',
                        ((outlook_pred_05 - outlook_pred_01) + dt).round(2)
                    )
                    if (outlook_pred_09 - outlook_pred_05) > (outlook_pred_05 - outlook_pred_01):
                        if ((outlook_pred_09 - outlook_pred_05) + dt) >= 6:
                            st.markdown(
                                "stability check: <span style='color:red'>RED</span>",
                                unsafe_allow_html=True
                            )
                        elif ((outlook_pred_09 - outlook_pred_05) + dt) >= 5:
                            st.markdown(
                                "stability check: <span style='color:orange'>YELLOW</span>",
                                unsafe_allow_html=True
                            )
                        elif ((outlook_pred_09 - outlook_pred_05) + dt) >= 3:
                            st.markdown(
                                "stability check: <span style='color:green'>GREEN</span>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                "stability check: <span style='color:blue'>BLUE (inefficient heating)</span>",
                                unsafe_allow_html=True
                            )
                    elif (outlook_pred_09 - outlook_pred_05) < (outlook_pred_05 - outlook_pred_01):
                        if dt > 6:
                            st.markdown(
                                "stability check: <span style='color:red'>RED</span>",
                                unsafe_allow_html=True
                            )
                        elif dt >= 5:
                            st.markdown(
                                "stability check: <span style='color:orange'>YELLOW</span>",
                                unsafe_allow_html=True
                            )
                        elif dt >= 3:
                            st.markdown(
                                "stability check: <span style='color:green'>GREEN</span>",
                                unsafe_allow_html=True
                            )
                        elif dt < 3:
                            st.markdown(
                                "stability check: <span style='color:blue'>BLUE (inefficient heating)</span>",
                                unsafe_allow_html=True
                            )
                else:
                    dt = (outlook_pred_05 - inlet_temp).round(2)
                    st.write("expected DT is around:", dt)
                    if dt > 6:
                        st.markdown(
                            "stability check: <span style='color:red'>RED</span>",
                            unsafe_allow_html=True
                        )
                    elif dt >= 5:
                        st.markdown(
                            "stability check: <span style='color:orange'>YELLOW</span>",
                            unsafe_allow_html=True
                        )
                    elif dt >= 3:
                        st.markdown(
                            "stability check: <span style='color:green'>GREEN</span>",
                            unsafe_allow_html=True
                        )
                    elif dt < 3:
                        st.markdown(
                            "stability check: <span style='color:blue'>BLUE (inefficient heating)</span>",
                            unsafe_allow_html=True
                        )
            else:
                st.write("PUE is showing inefficient energy system")
if __name__ == '__main__':
    w, it, at, s_id, s_name = collect_inputs()

    if st.button('run system'):
        cooling_pred, outlook_pred_01, outlook_pred_05, outlook_pred_09 = get_predictions( w, it, at, s_name)
        results(w, it, s_id, cooling_pred, outlook_pred_01, outlook_pred_05, outlook_pred_09)