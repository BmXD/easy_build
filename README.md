## What's Easy build ##
    easy build 是個 build framework
    利用 docker 將編譯環境容器化, 提供一致的編譯環境
    framework 也提供 dependent project 和 prebuilt lib 管理


## Usage ##
    usage: build.py [-h] [-u] [-b BRANCH] [-d] [-i] [-p] [-x DEPENDENCY_DEPTH] platform project

    platform, 編譯平台
        framework 會用先 docker images 去看要編譯的平台是否存在
        若不存在, 會利用 easy_build/docker 目錄下的 Dockerfile 去建立 container
        預設支援的 Dockerfile 命名規則為 Dockerfile.{PLATFORM}

    project, 要編譯的 project
        framework 會先去與 easy_build 同層的目錄搜尋 project
        ex: /source/easy_build, 會去 /source 下搜尋
        若 project 不存在, 才會去 gitlab 下載

    -u, 更新 project
        git pull 去更新 project, 包含需要編譯的相依 project
        如果有 local modified, 會先 git stash, 更新完之後再 pop, 不會解 conflict

    -b BRANCH, 要編譯 project 的 branch
        指定要編譯的 branch，若有 local modified，會 git stash 後再切換 branch
        若沒有指定, 不會進行切換 branch
        所有相依 project 皆會受到此參數影響, 除非 config 有指定相依 project 的 branch

    -r  將 platform 所安裝的 prebuilts 完全清除

    -d, 只安裝 project 所需的 prebuilt
        主會安裝 project 所需的 prebuilt lib, 不會執行編譯

    -i, 在 project 編譯完成後, 執行安裝
        在編譯完成後, 執行 install script
        若沒有加 -i，編譯完的產物只會留在原 project

    -p, 在 project 編譯完成後, 將編譯產物打包成壓縮檔
        在編譯完成後, 執行 package script
        打包完成的壓縮檔會放在 easy_build/{PLATFORM} 中
        檔名格式為 {PROJECT}_{VERSION}_{PLATFORM}.tar.xz
        只會打包指定的 project

    -x DEPENDENCY_DEPTH, 編譯相依 project 的深度, -1 為全部編譯

                                       depend             depend
                 depend              |--------> projectC --------> projectE
       projectA --------> projectB --|
                                     |--------> projectD
                                       depend
        depth 0            depth 1              depth 2             depth 3


       以編譯 projectA 為例:
       若 -x 0 或沒加 -x, 只會編譯 projectA
       並安裝 projectA 的 prebuilt

       若 -x 1, 表示會編譯到深度 1 的相依 project: projectB
       安裝 projectB 的 prebuilt
       並將 projectB 的編譯產物安裝到環境中(無論有沒有加 -i)

       若 -x 2，表示會編譯到深度 2 的相依 proejct: projectC, projectD, projectB
       安裝相依 projectB, projectC, projectD 的 prebuilt
       並將相依 project 的編譯產物安裝到環境裝(無論有沒有加 -i)


## framework config ##
    要將 project 支援 easy_build
    只需在 project 中加入 BuildConf 資料夾, 並依照需求加入下列 config

    build
      project 的 build script 

    install
      project 的 install script
      目的是將編譯後的產物安裝到系統中

    package
      project 的 package script
      目的是將編譯後的產物安裝至 $PACKAGE_TMP_DIR
      framework 會將其內容打包成壓縮檔: {PROJECT}_{VERSION}_{PLARFORM}.tar.xz
      若有東西不想被打包, 可在此 script 進行刪除

    version
      project 的版本號, 只會用於 package 時

    depends
      project 的 dependency config
      分為兩個 section: dependent 和 prebuilt

      dependent
        相依的 project
        欲編譯的 project 在編譯時, 會需要相依於最新版的 dependent project
        舉例來說, cvi_pipeline 相依於 networks
        表示 cvi_pipeline 每次編譯時, 都需要相依於最新版的 networks

      prebuilt
        相依的 prebuilt lib
        欲編譯的 project 在編譯時, 只需要固定版本的 lib
        便可將該版本的 lib 預先編譯好
        framework 會依照 config 去下載並安裝於系統

      config example:

        '''
        [dependent]
        networks = sdk_sample_improvement
        gst-plugins-good-1.x

        [prebuilt]
        glib-2.x = 2.16
        gstreamer-1.x = 1.14.5
        '''

        表示相依於 networks 的 sdk_sample_improvement branch 和 gst-plugins-good-1.x (無特定branch)
        需要 glib-2.x 的 2.16 版本和 gstreamer-1.x 的 1.14.5 版本的 prebuilt


## Tools ##
    有時在開發時, 不需要用到 framework 去編譯整個 project
    easy_build 有提供 tool,  可以快速進入 docker 環境中進行編譯
    並將該 platform 所需的 lib 目錄掛載至 docker 環境中

    usage: ./into [platform]

