import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    width: 284
    height: Math.min(500, 174 + Math.max(1, clopen.groupItems.length) * 36)
    visible: false
    color: "transparent"
    title: "Clopen"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint | Qt.WindowStaysOnTopHint

    readonly property bool darkMode: clopen.darkMode
    readonly property color textPrimary: darkMode ? "#F6F7FA" : "#20242A"
    readonly property color textSecondary: darkMode ? "#BAC2CD" : "#66707D"
    property bool closeArmed: false

    onVisibleChanged: {
        closeArmed = false
        if (visible) closeArmTimer.restart()
    }
    onActiveChanged: {
        if (visible && closeArmed && !active) visible = false
    }
    Timer {
        id: closeArmTimer
        interval: 220
        repeat: false
        onTriggered: root.closeArmed = true
    }

    GlassPane {
        anchors.fill: parent
        darkMode: root.darkMode
        cornerRadius: 18
        density: root.darkMode ? 0.038 : 0.095
        highlight: 0.09
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            spacing: 8
            Image {
                source: root.darkMode ? "../resources/clopen-logo-white.svg" : "../resources/clopen-logo-black.svg"
                sourceSize.width: 24
                sourceSize.height: 15
                Layout.preferredWidth: 24
                Layout.preferredHeight: 15
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: false
            }
            Text {
                text: "Clopen"
                color: root.textPrimary
                font.pixelSize: 14
                font.weight: Font.DemiBold
                renderType: Text.NativeRendering
                Layout.fillWidth: true
            }
        }

        GlassButton {
            text: "打开主界面"
            darkMode: root.darkMode
            quiet: true
            Layout.fillWidth: true
            implicitHeight: 34
            onClicked: { root.visible = false; clopen.showMain() }
        }

        Text {
            text: "快速启动"
            color: root.textSecondary
            font.pixelSize: 10
            font.weight: Font.DemiBold
            renderType: Text.NativeRendering
            Layout.leftMargin: 8
            Layout.topMargin: 3
        }

        Repeater {
            model: clopen.groupItems
            GlassButton {
                required property var modelData
                text: (modelData.active ? "关闭  " : "开启  ") + modelData.name
                darkMode: root.darkMode
                quiet: true
                Layout.fillWidth: true
                implicitHeight: 32
                onClicked: {
                    root.visible = false
                    clopen.toggleGroupByName(modelData.name)
                }
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: 3 }

        GlassButton {
            text: "设置"
            darkMode: root.darkMode
            quiet: true
            Layout.fillWidth: true
            implicitHeight: 32
            onClicked: { root.visible = false; clopen.showSettings() }
        }
        GlassButton {
            text: "退出 Clopen"
            darkMode: root.darkMode
            quiet: true
            Layout.fillWidth: true
            implicitHeight: 32
            onClicked: { root.visible = false; clopen.quitApplication() }
        }
    }

    Shortcut { sequence: "Escape"; onActivated: root.visible = false }
}
